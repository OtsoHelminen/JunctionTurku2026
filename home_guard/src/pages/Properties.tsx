import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { createHouse, fetchHouses } from '../api/houses';
import { isAbortError, RequestTimeoutError } from '../api/http';
import AddPropertyModal from '../components/properties/AddPropertyModal';
import OrderHelpSection from '../components/properties/OrderHelpSection';
import PropertySelector from '../components/properties/PropertySelector';
import ActiveAlertSection from '../components/properties/ActiveAlertSection';
import { getExpertSuggestions, sortAlerts } from '../components/properties/alert';
import { createRandomCoordinates, mapHouseToEntry } from '../components/properties/location';
import type { Coordinates, PropertyEntry } from '../components/properties/types';
import { useAlertNotifications } from '../components/properties/useAlertNotifications';
import { PROPERTY_ADDRESS_SAMPLES } from '../data/propertyAddressSamples';
import { useTheme } from '../theme/ThemeContext';

export default function Properties() {
  const { colors } = useTheme();
  const [properties, setProperties] = useState<PropertyEntry[]>([]);
  const [isLoadingProperties, setIsLoadingProperties] = useState(true);
  const [isCreatingProperty, setIsCreatingProperty] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [createError, setCreateError] = useState('');
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);
  const [isAddressModalVisible, setIsAddressModalVisible] = useState(false);
  const [addressInput, setAddressInput] = useState('');
  const [showAddressSuggestions, setShowAddressSuggestions] = useState(false);
  const [addressError, setAddressError] = useState('');
  const [previewCoordinates, setPreviewCoordinates] = useState<Coordinates | null>(null);
  // Lets Cancel (or leaving the screen) stop a pending create request
  const createAbortRef = useRef<AbortController | null>(null);

  const allAlerts = useAlertNotifications();

  // Only the selected property's alerts, most urgent first
  const alerts = useMemo(
    () =>
      sortAlerts(
        allAlerts.filter(
          (alert) =>
            selectedPropertyId === null ||
            alert.houseId === null ||
            alert.houseId === selectedPropertyId
        )
      ),
    [allAlerts, selectedPropertyId]
  );
  const expertSuggestions = useMemo(() => getExpertSuggestions(alerts), [alerts]);

  const addressSuggestions =
    showAddressSuggestions && addressInput.trim().length >= 2
      ? PROPERTY_ADDRESS_SAMPLES.filter((address) =>
          address
            .toLocaleLowerCase('fi-FI')
            .includes(addressInput.trim().toLocaleLowerCase('fi-FI'))
        ).slice(0, 5)
      : [];

  // Bumped by "Try again" to re-run the load effect
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    const loadHouses = async () => {
      try {
        const houses = await fetchHouses(controller.signal);
        const entries = houses.map(mapHouseToEntry);
        setProperties(entries);
        setSelectedPropertyId((current) =>
          entries.some((entry) => entry.id === current) ? current : (entries[0]?.id ?? null)
        );
      } catch (error: unknown) {
        if (isAbortError(error)) return; // screen left, nothing to show
        console.warn('Failed to load properties', error);
        setLoadError(
          error instanceof RequestTimeoutError
            ? "The server didn't respond. Check your connection and try again."
            : "Couldn't load properties. Check your connection and try again."
        );
      } finally {
        if (!controller.signal.aborted) setIsLoadingProperties(false);
      }
    };

    void loadHouses();
    return () => controller.abort();
  }, [loadAttempt]);

  // Leaving the screen also cancels a pending create request
  useEffect(() => () => createAbortRef.current?.abort(), []);

  const retryLoadingHouses = () => {
    setIsLoadingProperties(true);
    setLoadError('');
    setLoadAttempt((attempt) => attempt + 1);
  };

  const handleAddProperty = async () => {
    const address = addressInput.trim();
    if (!address) {
      setAddressError('Enter a property address to continue.');
      return;
    }

    const controller = new AbortController();
    createAbortRef.current = controller;
    setIsCreatingProperty(true);
    setCreateError('');
    try {
      const coordinates = previewCoordinates ?? createRandomCoordinates(address);
      const house = await createHouse({ address, ...coordinates }, controller.signal);
      const newProperty = mapHouseToEntry(house);
      setProperties((currentProperties) => [
        ...currentProperties.filter((current) => current.id !== newProperty.id),
        newProperty,
      ]);
      setSelectedPropertyId(newProperty.id);
      resetAddressModal();
    } catch (error: unknown) {
      if (isAbortError(error)) return; // cancelled by the user
      // Never show the raw exception to the user
      console.warn('Failed to create property', error);
      setCreateError(
        error instanceof RequestTimeoutError
          ? "The server didn't respond. Check your connection and try again."
          : "Couldn't create property. Check your connection and try again."
      );
    } finally {
      if (createAbortRef.current === controller) createAbortRef.current = null;
      setIsCreatingProperty(false);
    }
  };

  // Cancel always works, even while a request is pending: it aborts the request
  const handleCloseAddressModal = () => {
    createAbortRef.current?.abort();
    createAbortRef.current = null;
    setIsCreatingProperty(false);
    setCreateError('');
    resetAddressModal();
  };

  const resetAddressModal = () => {
    setAddressInput('');
    setShowAddressSuggestions(false);
    setAddressError('');
    setPreviewCoordinates(null);
    setIsAddressModalVisible(false);
  };

  const handleSelectAddressSuggestion = (address: string) => {
    setAddressInput(address);
    setShowAddressSuggestions(false);
    setPreviewCoordinates(createRandomCoordinates(address));
    setAddressError('');
  };

  return (
    <>
      <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={styles.container}>
        <PropertySelector
          entries={properties}
          isLoading={isLoadingProperties}
          selectedId={selectedPropertyId}
          error={loadError}
          onSelect={setSelectedPropertyId}
          onRetry={retryLoadingHouses}
          onAdd={() => {
            setCreateError('');
            setIsAddressModalVisible(true);
          }}
        />

        <ActiveAlertSection alerts={alerts} />
        <OrderHelpSection experts={expertSuggestions} />
      </ScrollView>

      <AddPropertyModal
        visible={isAddressModalVisible}
        address={addressInput}
        addressSuggestions={addressSuggestions}
        showAddressSuggestions={showAddressSuggestions}
        addressError={addressError}
        propertyError={createError}
        previewCoordinates={previewCoordinates}
        isCreating={isCreatingProperty}
        onClose={handleCloseAddressModal}
        onAdd={handleAddProperty}
        onAddressChange={(value) => {
          setAddressInput(value);
          setShowAddressSuggestions(true);
          setPreviewCoordinates(null);
          if (addressError) setAddressError('');
        }}
        onAddressFocus={() => setShowAddressSuggestions(true)}
        onSelectAddressSuggestion={handleSelectAddressSuggestion}
      />
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 24,
    gap: 22,
  },
});
