import { useEffect, useSyncExternalStore } from 'react';
import * as Notifications from 'expo-notifications';
import { parseAlertNotification } from './alert';
import type { AlertEntry } from './alert';

// Small shared store so alerts survive the screen unmounting (for the app session).
const alertsById = new Map<number, AlertEntry>();
const listeners = new Set<() => void>();
let snapshot: AlertEntry[] = [];

const emit = () => {
  snapshot = Array.from(alertsById.values());
  listeners.forEach((listener) => listener());
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

const getSnapshot = () => snapshot;

const ingest = (content: Notifications.NotificationContent) => {
  const alert = parseAlertNotification(content);
  if (!alert) return;

  if (alert.status === 'active') {
    alertsById.set(alert.id, alert); // same alert_id updates the existing card
  } else {
    alertsById.delete(alert.id); // resolved / dismissed alerts disappear
  }
  emit();
};

/**
 * Listens for incoming alert notifications and returns all active alerts.
 * Safe to call from several places (e.g. once in the root layout so alerts
 * are captured before this screen is first opened).
 */
export function useAlertNotifications(): AlertEntry[] {
  useEffect(() => {
    const loadExisting = async () => {
      try {
        // Notifications already sitting in the notification tray
        const presented = await Notifications.getPresentedNotificationsAsync();
        presented.forEach((notification) => ingest(notification.request.content));

        // Notification that opened the app from a closed state
        const lastResponse = await Notifications.getLastNotificationResponseAsync();
        if (lastResponse) ingest(lastResponse.notification.request.content);
      } catch {
        // Not supported on this platform; live notifications still work.
      }
    };
    void loadExisting();

    const receivedSubscription = Notifications.addNotificationReceivedListener((notification) =>
      ingest(notification.request.content)
    );
    const responseSubscription = Notifications.addNotificationResponseReceivedListener((response) =>
      ingest(response.notification.request.content)
    );

    return () => {
      receivedSubscription.remove();
      responseSubscription.remove();
    };
  }, []);

  return useSyncExternalStore(subscribe, getSnapshot);
}
