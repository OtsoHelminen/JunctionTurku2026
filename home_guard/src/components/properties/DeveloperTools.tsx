import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import * as Notifications from 'expo-notifications';
import { registerForPush, sendTestLocalNotification } from '../../api/notifications';
import { FONTS, useTheme } from '../../theme/ThemeContext';
import type { ReceivedNotificationInfo } from './types';

export default function DeveloperTools() {
  const { colors } = useTheme();
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('Press button to request token');
  const [isError, setIsError] = useState(false);
  const [lastNotification, setLastNotification] = useState<ReceivedNotificationInfo | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const receivedSubscription = Notifications.addNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification.request.content);
      setLastNotification({
        title: notification.request.content.title,
        body: notification.request.content.body,
        data: (notification.request.content.data as Record<string, unknown>) ?? {},
      });
    });

    const responseSubscription = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        console.log('Notification tapped:', response.notification.request.content);
        const data = response.notification.request.content.data as { id?: string; type?: string };
        if (data?.id) {
          setStatusMessage(`Tapped notification: ${data.type ?? 'item'} #${data.id}`);
        }
      }
    );

    return () => {
      receivedSubscription.remove();
      responseSubscription.remove();
    };
  }, []);

  const handleRequestToken = async () => {
    setLoading(true);
    setIsError(false);
    setStatusMessage('Requesting push permissions & token...');

    try {
      const result = await registerForPush();
      if (result.token) {
        setToken(result.token);
        setIsError(false);
        setStatusMessage('Success! Push token generated.');
      } else {
        setIsError(true);
        setStatusMessage(result.error ?? 'Failed to get push token.');
      }
    } catch (err: unknown) {
      setIsError(true);
      const message = err instanceof Error ? err.message : String(err);
      setStatusMessage(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendTestNotification = async () => {
    try {
      await sendTestLocalNotification();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setStatusMessage(`Failed to send test: ${message}`);
    }
  };

  return (
    <View>
      <Pressable
        style={styles.developerToolsToggle}
        onPress={() => setIsExpanded((expanded) => !expanded)}
        android_ripple={{ color: colors.accentSoft }}
        accessibilityRole="button"
        accessibilityLabel="Developer tools"
        accessibilityState={{ expanded: isExpanded }}
      >
        <MaterialIcons name="code" size={26} color={colors.text} />
        <Text style={[styles.developerToolsTitle, { color: colors.text }]}>Developer tools</Text>
        <MaterialIcons
          name={isExpanded ? 'expand-less' : 'expand-more'}
          size={24}
          color={colors.muted}
        />
      </Pressable>
      {isExpanded && (
        <View style={styles.developerToolsContent}>
          <Text style={[styles.subheading, { color: colors.muted }]}>Push Notification Tester</Text>

          <View style={styles.buttonGroup}>
            <Pressable
              style={({ pressed }) => [
                styles.button,
                { backgroundColor: colors.accent },
                (pressed || loading) && styles.buttonPressed,
              ]}
              onPress={handleRequestToken}
              disabled={loading}
              accessibilityRole="button"
            >
              {loading ? (
                <ActivityIndicator color={colors.onAccent} />
              ) : (
                <Text style={[styles.buttonText, { color: colors.onAccent }]}>
                  Request Push Token
                </Text>
              )}
            </Pressable>

            <Pressable
              style={({ pressed }) => [
                styles.button,
                { backgroundColor: colors.surface2 },
                pressed && styles.buttonPressed,
              ]}
              onPress={handleSendTestNotification}
              accessibilityRole="button"
            >
              <Text style={[styles.buttonText, { color: colors.text }]}>
                Send Test Notification
              </Text>
            </Pressable>
          </View>

          <View
            style={[
              styles.card,
              {
                backgroundColor: colors.surface,
                borderColor: isError ? colors.error : colors.line,
              },
            ]}
          >
            <Text style={[styles.cardLabel, { color: colors.muted }]}>Status</Text>
            <Text style={[styles.cardText, { color: isError ? colors.error : colors.text }]}>
              {statusMessage}
            </Text>
          </View>

          {token && (
            <View
              style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}
            >
              <Text style={[styles.cardLabel, { color: colors.muted }]}>
                Expo Push Token (Select & Copy):
              </Text>
              <Text
                style={[styles.mono, { color: colors.text, backgroundColor: colors.surface2 }]}
                selectable
              >
                {token}
              </Text>
            </View>
          )}

          {lastNotification && (
            <View
              style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}
            >
              <Text style={[styles.cardLabel, { color: colors.muted }]}>
                Last Received Notification:
              </Text>
              <Text style={[styles.notificationTitle, { color: colors.text }]}>
                {lastNotification.title ?? 'No title'}
              </Text>
              <Text style={[styles.cardText, { color: colors.muted }]}>
                {lastNotification.body ?? 'No body'}
              </Text>
              {Object.keys(lastNotification.data).length > 0 && (
                <Text
                  style={[styles.mono, { color: colors.muted, backgroundColor: colors.surface2 }]}
                  selectable
                >
                  Data: {JSON.stringify(lastNotification.data, null, 2)}
                </Text>
              )}
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  developerToolsToggle: {
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingHorizontal: 16,
  },
  developerToolsTitle: {
    flex: 1,
    fontFamily: FONTS.body,
    fontSize: 17,
  },
  developerToolsContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    gap: 12,
  },
  subheading: {
    fontFamily: FONTS.body,
    fontSize: 14,
  },
  buttonGroup: {
    gap: 12,
  },
  button: {
    height: 52,
    borderRadius: 26,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonPressed: {
    opacity: 0.85,
  },
  buttonText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 17,
  },
  card: {
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    gap: 6,
  },
  cardLabel: {
    fontFamily: FONTS.bodyBold,
    fontSize: 13,
    textTransform: 'uppercase',
  },
  cardText: {
    fontFamily: FONTS.body,
    fontSize: 15,
  },
  notificationTitle: {
    fontFamily: FONTS.bodyBold,
    fontSize: 16,
  },
  mono: {
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }),
    fontSize: 12,
    padding: 10,
    borderRadius: 8,
  },
});
