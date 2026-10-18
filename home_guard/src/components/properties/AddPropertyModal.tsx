import React, { useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { FONTS, useTheme } from '../../theme/ThemeContext';
import MapPreview from './MapPreview';
import type { Coordinates } from './types';

interface AddPropertyModalProps {
  visible: boolean;
  address: string;
  addressSuggestions: string[];
  showAddressSuggestions: boolean;
  addressError: string;
  propertyError: string;
  previewCoordinates: Coordinates | null;
  isCreating: boolean;
  onClose: () => void;
  onAdd: () => void;
  onAddressChange: (address: string) => void;
  onAddressFocus: () => void;
  onSelectAddressSuggestion: (address: string) => void;
}

export default function AddPropertyModal({
  visible,
  address,
  addressSuggestions,
  showAddressSuggestions,
  addressError,
  propertyError,
  previewCoordinates,
  isCreating,
  onClose,
  onAdd,
  onAddressChange,
  onAddressFocus,
  onSelectAddressSuggestion,
}: AddPropertyModalProps) {
  const { colors } = useTheme();
  const [isFocused, setIsFocused] = useState(false);
  const errorMessage = addressError || propertyError;

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
        {/* Tapping the scrim closes the dialog */}
        <Pressable
          style={[StyleSheet.absoluteFill, { backgroundColor: colors.scrim }]}
          onPress={onClose}
          accessibilityLabel="Close dialog"
        />
        <View style={[styles.modalCard, { backgroundColor: colors.surface }]}>
          <ScrollView
            style={styles.modalScroll}
            contentContainerStyle={styles.modalContent}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={[styles.modalTitle, { color: colors.text }]}>Add a property</Text>
            <Text style={[styles.modalDescription, { color: colors.muted }]}>
              Enter the address of the property you want to add.
            </Text>
            <View>
              <TextInput
                style={[
                  styles.addressInput,
                  { backgroundColor: colors.surface, color: colors.text },
                  isFocused
                    ? { borderColor: colors.accent, borderWidth: 2, paddingHorizontal: 13 }
                    : { borderColor: colors.line },
                  addressError ? { borderColor: colors.error } : null,
                ]}
                value={address}
                onChangeText={onAddressChange}
                onFocus={() => {
                  setIsFocused(true);
                  onAddressFocus();
                }}
                onBlur={() => setIsFocused(false)}
                placeholder="Address"
                placeholderTextColor={colors.muted}
                selectionColor={colors.accent}
                autoCapitalize="words"
                autoCorrect={false}
                spellCheck={false}
                autoComplete="off"
                importantForAutofill="no"
                textContentType="none"
                returnKeyType="done"
                onSubmitEditing={onAdd}
                editable={!isCreating}
                accessibilityLabel="Property address"
              />
              {showAddressSuggestions && addressSuggestions.length > 0 && (
                <View
                  style={[
                    styles.addressSuggestions,
                    { backgroundColor: colors.surface, borderColor: colors.line },
                  ]}
                >
                  {addressSuggestions.map((suggestion) => (
                    <Pressable
                      key={suggestion}
                      style={[styles.addressSuggestion, { borderBottomColor: colors.line }]}
                      onPress={() => onSelectAddressSuggestion(suggestion)}
                      android_ripple={{ color: colors.accentSoft }}
                      accessibilityRole="button"
                      accessibilityLabel={`Use address ${suggestion}`}
                    >
                      <MaterialIcons name="location-on" size={20} color={colors.muted} />
                      <Text style={[styles.addressSuggestionText, { color: colors.text }]}>
                        {suggestion}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              )}
            </View>
            {errorMessage ? (
              <View style={styles.errorRow} accessibilityLiveRegion="polite">
                <MaterialIcons name="error" size={20} color={colors.error} />
                <Text style={[styles.errorText, { color: colors.error }]}>{errorMessage}</Text>
              </View>
            ) : null}
            {previewCoordinates ? (
              <>
                <Text style={[styles.mapTitle, { color: colors.text }]}>Location</Text>
                <MapPreview
                  key={`${previewCoordinates.latitude}-${previewCoordinates.longitude}`}
                  coordinates={previewCoordinates}
                />
                <View>
                  <Text style={[styles.mapMeta, { color: colors.muted }]}>
                    {`Latitude ${previewCoordinates.latitude.toFixed(4)}, Longitude ${previewCoordinates.longitude.toFixed(4)}`}
                  </Text>
                  <Text style={[styles.mapMeta, { color: colors.muted }]}>
                    © OpenStreetMap contributors
                  </Text>
                </View>
              </>
            ) : null}
          </ScrollView>
          <View style={styles.modalActions}>
            <Pressable
              style={({ pressed }) => [
                styles.modalButton,
                { backgroundColor: colors.surface2 },
                (pressed || isCreating) && styles.buttonPressed,
              ]}
              onPress={onClose}
              disabled={isCreating}
              accessibilityRole="button"
            >
              <Text style={[styles.buttonText, { color: colors.text }]}>Cancel</Text>
            </Pressable>
            <Pressable
              style={({ pressed }) => [
                styles.modalButton,
                { backgroundColor: colors.accent },
                pressed && styles.buttonPressed,
              ]}
              onPress={onAdd}
              disabled={isCreating}
              accessibilityRole="button"
              accessibilityState={{ busy: isCreating, disabled: isCreating }}
            >
              {isCreating ? (
                <ActivityIndicator color={colors.onAccent} />
              ) : (
                <Text style={[styles.buttonText, { color: colors.onAccent }]}>OK</Text>
              )}
            </Pressable>
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
    paddingHorizontal: 14,
    paddingVertical: 24,
  },
  modalCard: {
    width: '100%',
    maxWidth: 440,
    maxHeight: '90%',
    borderRadius: 24,
    overflow: 'hidden',
    flexShrink: 1,
    boxShadow: '0px 20px 50px rgba(0,0,0,0.35)',
  },
  modalScroll: {
    flexGrow: 0,
    flexShrink: 1,
  },
  modalContent: {
    paddingHorizontal: 20,
    paddingTop: 20,
    gap: 12,
  },
  modalTitle: {
    fontFamily: FONTS.heading,
    fontSize: 22,
  },
  modalDescription: {
    fontFamily: FONTS.body,
    fontSize: 15,
    lineHeight: 21,
  },
  addressInput: {
    height: 56,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 14,
    fontFamily: FONTS.body,
    fontSize: 17,
  },
  addressSuggestions: {
    marginTop: 4,
    borderWidth: 1,
    borderRadius: 14,
    overflow: 'hidden',
  },
  addressSuggestion: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderBottomWidth: 1,
  },
  addressSuggestionText: {
    flex: 1,
    fontFamily: FONTS.body,
    fontSize: 15,
  },
  errorRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  errorText: {
    flex: 1,
    fontFamily: FONTS.body,
    fontSize: 14,
    lineHeight: 19,
  },
  mapTitle: {
    fontFamily: FONTS.bodyBold,
    fontSize: 14,
  },
  mapMeta: {
    marginTop: 2,
    fontFamily: FONTS.body,
    fontSize: 13,
    textAlign: 'center',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 20,
  },
  modalButton: {
    flex: 1,
    height: 52,
    borderRadius: 26,
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
});
