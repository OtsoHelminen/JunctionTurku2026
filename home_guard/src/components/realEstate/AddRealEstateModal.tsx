import React from 'react';
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import MapPreview from './MapPreview';
import type { Coordinates } from './types';

interface AddRealEstateModalProps {
  visible: boolean;
  address: string;
  addressSuggestions: string[];
  showAddressSuggestions: boolean;
  addressError: string;
  realEstateError: string;
  previewCoordinates: Coordinates | null;
  isCreating: boolean;
  onClose: () => void;
  onAdd: () => void;
  onAddressChange: (address: string) => void;
  onAddressFocus: () => void;
  onSelectAddressSuggestion: (address: string) => void;
}

export default function AddRealEstateModal({
  visible,
  address,
  addressSuggestions,
  showAddressSuggestions,
  addressError,
  realEstateError,
  previewCoordinates,
  isCreating,
  onClose,
  onAdd,
  onAddressChange,
  onAddressFocus,
  onSelectAddressSuggestion,
}: AddRealEstateModalProps) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      navigationBarTranslucent
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView style={styles.modalBackdrop} behavior="padding">
        <View style={styles.modalCard}>
          <ScrollView
            style={styles.modalScroll}
            contentContainerStyle={styles.modalContent}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.modalTitle}>Add a real estate</Text>
            <Text style={styles.modalDescription}>
              Enter the address of the real estate you want to add.
            </Text>
            <TextInput
              style={[styles.addressInput, addressError && styles.addressInputError]}
              value={address}
              onChangeText={onAddressChange}
              onFocus={onAddressFocus}
              placeholder="Address"
              placeholderTextColor="#94a3b8"
              autoCapitalize="words"
              autoCorrect={false}
              spellCheck={false}
              autoComplete="off"
              importantForAutofill="no"
              textContentType="none"
              returnKeyType="done"
              onSubmitEditing={onAdd}
              accessibilityLabel="Real estate address"
            />
            {showAddressSuggestions && addressSuggestions.length > 0 && (
              <View style={styles.addressSuggestions}>
                {addressSuggestions.map((suggestion) => (
                  <TouchableOpacity
                    key={suggestion}
                    style={styles.addressSuggestion}
                    onPress={() => onSelectAddressSuggestion(suggestion)}
                    activeOpacity={0.7}
                    accessibilityRole="button"
                    accessibilityLabel={`Use address ${suggestion}`}
                  >
                    <Ionicons name="location-outline" size={18} color="#64748b" />
                    <Text style={styles.addressSuggestionText}>{suggestion}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
            {addressError ? <Text style={styles.addressError}>{addressError}</Text> : null}
            {realEstateError ? <Text style={styles.addressError}>{realEstateError}</Text> : null}
            {previewCoordinates ? (
              <View style={styles.mapSection}>
                <Text style={styles.mapTitle}>Location</Text>
                <MapPreview
                  key={`${previewCoordinates.latitude}-${previewCoordinates.longitude}`}
                  coordinates={previewCoordinates}
                />
                <Text style={styles.coordinatesText}>
                  {`Latitude ${previewCoordinates.latitude.toFixed(4)}, Longitude ${previewCoordinates.longitude.toFixed(4)}`}
                </Text>
                <Text style={styles.mapAttribution}>© OpenStreetMap contributors</Text>
              </View>
            ) : null}
          </ScrollView>
          <View style={styles.modalActions}>
            <TouchableOpacity
              style={[styles.modalButton, styles.cancelButton]}
              onPress={onClose}
              disabled={isCreating}
              activeOpacity={0.8}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.modalButton,
                styles.confirmButton,
                isCreating && styles.buttonDisabled,
              ]}
              onPress={onAdd}
              disabled={isCreating}
              activeOpacity={0.8}
            >
              {isCreating ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text style={styles.confirmButtonText}>OK</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalBackdrop: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
  },
  modalCard: {
    width: '100%',
    maxWidth: 440,
    maxHeight: '90%',
    backgroundColor: '#ffffff',
    borderRadius: 16,
    overflow: 'hidden',
    flexShrink: 1,
  },
  modalScroll: {
    flexGrow: 0,
    flexShrink: 1,
  },
  modalContent: {
    paddingHorizontal: 20,
    paddingTop: 20,
    flexGrow: 0,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0f172a',
  },
  modalDescription: {
    marginTop: 6,
    marginBottom: 16,
    fontSize: 14,
    color: '#64748b',
  },
  addressInput: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 10,
    paddingHorizontal: 12,
    color: '#0f172a',
    fontSize: 15,
  },
  addressInputError: {
    borderColor: '#dc2626',
  },
  addressSuggestions: {
    marginTop: 4,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    backgroundColor: '#ffffff',
    overflow: 'hidden',
  },
  addressSuggestion: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  addressSuggestionText: {
    flex: 1,
    color: '#334155',
    fontSize: 14,
  },
  addressError: {
    marginTop: 6,
    color: '#dc2626',
    fontSize: 12,
  },
  mapSection: {
    marginTop: 16,
  },
  mapTitle: {
    marginBottom: 8,
    color: '#334155',
    fontSize: 13,
    fontWeight: '600',
  },
  coordinatesText: {
    marginTop: 8,
    color: '#334155',
    fontSize: 12,
    textAlign: 'center',
  },
  mapAttribution: {
    marginTop: 3,
    color: '#64748b',
    fontSize: 10,
    textAlign: 'right',
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 20,
  },
  modalButton: {
    minWidth: 84,
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 9,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: '#f1f5f9',
  },
  cancelButtonText: {
    color: '#334155',
    fontSize: 14,
    fontWeight: '600',
  },
  confirmButton: {
    backgroundColor: '#2563eb',
  },
  confirmButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
