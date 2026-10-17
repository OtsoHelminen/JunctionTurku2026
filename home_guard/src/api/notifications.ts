import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import {
  AndroidImportance,
  AndroidNotificationPriority,
  AndroidNotificationVisibility,
} from 'expo-notifications';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { API_URL } from './config';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPush(): Promise<{ token: string | null; error?: string }> {
  if (!Device.isDevice) {
    return {
      token: null,
      error: 'Must use a physical device for Expo Push Notifications.',
    };
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Important Alerts',
      importance: AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#2563eb',
      sound: 'default',
      enableVibrate: true,
      showBadge: true,
      lockscreenVisibility: AndroidNotificationVisibility.PUBLIC,
    });
  }

  const { status: existing } = await Notifications.getPermissionsAsync();
  let status = existing;
  if (existing !== 'granted') {
    status = (
      await Notifications.requestPermissionsAsync({
        ios: {
          allowAlert: true,
          allowBadge: true,
          allowSound: true,
        },
      })
    ).status;
  }
  if (status !== 'granted') {
    return {
      token: null,
      error: 'Permission not granted for notifications.',
    };
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;

  try {
    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });

    // Attempt to register device with backend API (fails gracefully if backend is offline)
    try {
      await fetch(`${API_URL}/app/devices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, platform: Platform.OS }),
      });
    } catch {
      console.warn('Backend server not reachable at', API_URL);
    }

    console.log('Push notification token:', token);
    return { token };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('Failed to get Expo push token:', message);
    return { token: null, error: message };
  }
}

export async function sendTestLocalNotification(): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: 'Toimenpidesuositus – Helsinki',
      body: 'Clean the gutters and downspouts before the rain\nSuggested expert: Roofer, approx. 150–400 €',
      sound: true,
      priority: AndroidNotificationPriority.MAX,
      data: {
        kind: 'alert',
        event_id: 7,
        event_type: 'analyzed',
        alert_id: 3,
        fingerprint: 'wind:house-1',
        rule_id: 'severe_storm',
        source_id: 'house-1',
        house_id: 1,
        area: 'Helsinki',
        severity: 'critical',
        category: 'katto',
        status: 'active',
        message: 'Kova myrsky kohteessa house-1: tuuli 24.5 m/s',
        recommendation: 'Clean the gutters and downspouts before the rain',
        urgency: 'today',
        expert: {
          registered: false,
          profession: 'Roofer',
          example_name: 'Example Roofing Ltd',
          price_min_eur: 150,
          price_max_eur: 400,
        },
        created_at: '2026-10-17T10:05:00Z',
      },
    },
    trigger: null,
  });
}

export async function unregisterPush(token: string) {
  try {
    await fetch(`${API_URL}/app/devices?token=${encodeURIComponent(token)}`, {
      method: 'DELETE',
    });
  } catch {
    console.warn('Backend server not reachable at', API_URL);
  }
}
