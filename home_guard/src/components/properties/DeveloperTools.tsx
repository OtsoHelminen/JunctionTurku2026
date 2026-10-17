import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Notifications from 'expo-notifications';
import { registerForPush, sendTestLocalNotification } from '../../api/notifications';
import { useTheme } from '../../theme/ThemeContext';
import type { ReceivedNotificationInfo } from './types';

export default function DeveloperTools() {
  const { colors, isDark } = useTheme();
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
    <>
      <TouchableOpacity
        style={[styles.developerToolsToggle, { borderTopColor: colors.border }]}
        onPress={() => setIsExpanded((expanded) => !expanded)}
        activeOpacity={0.75}
        accessibilityRole="button"
        accessibilityLabel="Developer tools"
        accessibilityState={{ expanded: isExpanded }}
      >
        <Text style={[styles.developerToolsTitle, { color: colors.mutedText }]}>
          Developer tools
        </Text>
        <Ionicons
          name={isExpanded ? 'chevron-up' : 'chevron-down'}
          size={18}
          color={colors.mutedText}
        />
      </TouchableOpacity>
      {isExpanded && (
        <View style={styles.developerToolsContent}>
          <Text style={[styles.subheading, { color: colors.mutedText }]}>
            Push Notification Tester
          </Text>

          <View style={styles.buttonGroup}>
            <TouchableOpacity
              style={[styles.button, styles.primaryButton, loading && styles.buttonDisabled]}
              onPress={handleRequestToken}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text style={styles.primaryButtonText}>Request Push Token</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.button,
                styles.secondaryButton,
                { backgroundColor: colors.surface, borderColor: colors.inputBorder },
              ]}
              onPress={handleSendTestNotification}
              activeOpacity={0.8}
            >
              <Text style={[styles.secondaryButtonText, { color: colors.secondaryText }]}>
                Send Test Notification
              </Text>
            </TouchableOpacity>
          </View>

          <View
            style={[
              styles.card,
              isError ? styles.cardError : [styles.cardInfo, isDark && styles.darkCardInfo],
            ]}
          >
            <Text style={[styles.cardLabel, { color: colors.mutedText }]}>Status</Text>
            <Text style={[styles.cardText, { color: colors.text }, isError && styles.errorText]}>
              {statusMessage}
            </Text>
          </View>

          {token && (
            <View
              style={[
                styles.tokenCard,
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.cardLabel, { color: colors.mutedText }]}>
                Expo Push Token (Select & Copy):
              </Text>
              <Text
                style={[
                  styles.tokenText,
                  { color: colors.text, backgroundColor: colors.subtleSurface },
                ]}
                selectable
              >
                {token}
              </Text>
            </View>
          )}

          {lastNotification && (
            <View
              style={[
                styles.receivedCard,
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.cardLabel, { color: colors.mutedText }]}>
                Last Received Notification:
              </Text>
              <Text style={[styles.notificationTitle, { color: colors.text }]}>
                {lastNotification.title ?? 'No title'}
              </Text>
              <Text style={[styles.notificationBody, { color: colors.secondaryText }]}>
                {lastNotification.body ?? 'No body'}
              </Text>
              {Object.keys(lastNotification.data).length > 0 && (
                <Text
                  style={[
                    styles.notificationData,
                    { color: colors.mutedText, backgroundColor: colors.subtleSurface },
                  ]}
                  selectable
                >
                  Data: {JSON.stringify(lastNotification.data, null, 2)}
                </Text>
              )}
            </View>
          )}
        </View>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  developerToolsToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  developerToolsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748b',
  },
  developerToolsContent: {
    paddingTop: 4,
  },
  subheading: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 20,
  },
  buttonGroup: {
    gap: 12,
    marginBottom: 20,
  },
  button: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButton: {
    backgroundColor: '#2563eb',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  secondaryButtonText: {
    color: '#334155',
    fontSize: 15,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  card: {
    padding: 16,
    borderRadius: 10,
    marginBottom: 16,
    borderWidth: 1,
  },
  cardInfo: {
    backgroundColor: '#eff6ff',
    borderColor: '#bfdbfe',
  },
  darkCardInfo: {
    backgroundColor: '#172554',
    borderColor: '#1e40af',
  },
  cardError: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    color: '#64748b',
    marginBottom: 6,
  },
  cardText: {
    fontSize: 14,
    color: '#1e293b',
  },
  errorText: {
    color: '#dc2626',
    fontWeight: '500',
  },
  tokenCard: {
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 16,
  },
  tokenText: {
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }),
    fontSize: 12,
    color: '#0f172a',
    backgroundColor: '#f1f5f9',
    padding: 10,
    borderRadius: 6,
    marginTop: 6,
  },
  receivedCard: {
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  notificationTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
    marginTop: 4,
  },
  notificationBody: {
    fontSize: 14,
    color: '#475569',
    marginTop: 2,
  },
  notificationData: {
    fontSize: 11,
    color: '#64748b',
    backgroundColor: '#f1f5f9',
    padding: 8,
    borderRadius: 6,
    marginTop: 8,
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }),
  },
});
