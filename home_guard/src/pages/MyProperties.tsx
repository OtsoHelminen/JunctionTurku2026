import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  BackHandler,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { fetchHouses } from '../api/houses';
import type { House } from '../api/houses';
import { isAbortError } from '../api/http';
import { FONTS, useTheme } from '../theme/ThemeContext';

interface MyPropertiesProps {
  onBack: () => void;
}

export default function MyProperties({ onBack }: MyPropertiesProps) {
  const { colors } = useTheme();
  const [houses, setHouses] = useState<House[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  // Bumped by "Try again" to re-run the load effect
  const [loadAttempt, setLoadAttempt] = useState(0);

  // Android back button returns to Settings
  useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      onBack();
      return true;
    });
    return () => subscription.remove();
  }, [onBack]);

  useEffect(() => {
    const controller = new AbortController();

    const loadHouses = async () => {
      try {
        setHouses(await fetchHouses(controller.signal));
      } catch (loadError: unknown) {
        if (isAbortError(loadError)) return;
        console.warn('Failed to load properties', loadError);
        setError("Couldn't load properties. Check your connection and try again.");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    };

    void loadHouses();
    return () => controller.abort();
  }, [loadAttempt]);

  const retry = () => {
    setIsLoading(true);
    setError('');
    setLoadAttempt((attempt) => attempt + 1);
  };

  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={styles.container}>
      <View style={styles.titleRow}>
        <Pressable
          style={styles.backButton}
          onPress={onBack}
          android_ripple={{ color: colors.accentSoft, borderless: true }}
          accessibilityRole="button"
          accessibilityLabel="Back to settings"
        >
          <MaterialIcons name="arrow-back" size={26} color={colors.text} />
        </Pressable>
        <Text style={[styles.title, { color: colors.text }]} accessibilityRole="header">
          Your properties
        </Text>
      </View>

      {isLoading ? (
        <ActivityIndicator style={styles.spinner} color={colors.accentText} />
      ) : error ? (
        <View style={styles.errorRow}>
          <MaterialIcons name="error" size={20} color={colors.error} />
          <View style={styles.errorBody}>
            <Text style={[styles.errorText, { color: colors.error }]}>{error}</Text>
            <Pressable
              style={styles.retryButton}
              onPress={retry}
              accessibilityRole="button"
              accessibilityLabel="Try loading properties again"
            >
              <Text style={[styles.retryText, { color: colors.accentText }]}>Try again</Text>
            </Pressable>
          </View>
        </View>
      ) : houses.length === 0 ? (
        <Text style={[styles.empty, { color: colors.muted }]}>
          You haven&apos;t added any properties yet. Add one from the Home tab.
        </Text>
      ) : (
        houses.map((house) => (
          <View
            key={house.id}
            style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}
          >
            <MaterialIcons name="home" size={30} color={colors.accentText} />
            <View style={styles.cardBody}>
              <Text style={[styles.address, { color: colors.text }]}>{house.address}</Text>
              <Text style={[styles.meta, { color: colors.muted }]}>
                {`${house.latitude.toFixed(4)}, ${house.longitude.toFixed(4)}`}
              </Text>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 24,
    gap: 12,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginLeft: -12,
  },
  backButton: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontFamily: FONTS.heading,
    fontSize: 24,
  },
  spinner: {
    marginTop: 24,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
  },
  cardBody: {
    flex: 1,
    gap: 2,
  },
  address: {
    fontFamily: FONTS.bodyBold,
    fontSize: 18,
  },
  meta: {
    fontFamily: FONTS.body,
    fontSize: 15,
  },
  empty: {
    fontFamily: FONTS.body,
    fontSize: 16,
    lineHeight: 23,
  },
  errorRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  errorBody: {
    flex: 1,
    alignItems: 'flex-start',
  },
  errorText: {
    fontFamily: FONTS.body,
    fontSize: 14,
    lineHeight: 19,
  },
  retryButton: {
    minHeight: 48,
    justifyContent: 'center',
  },
  retryText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 15,
  },
});
