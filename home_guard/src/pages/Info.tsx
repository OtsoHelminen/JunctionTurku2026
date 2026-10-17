import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function Info() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Info</Text>
      <Text style={styles.subtitle}>Empty page</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#0f172a',
  },
  subtitle: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 8,
  },
});
