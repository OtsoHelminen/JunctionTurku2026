import React, { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { createHouse, fetchHouses } from '../api/houses';
import AddPropertyModal from '../components/properties/AddPropertyModal';
import DeveloperTools from '../components/properties/DeveloperTools';
import OrderHelpSection from '../components/properties/OrderHelpSection';
import PropertySelector from '../components/properties/PropertySelector';
import ActiveAlertSection from '../components/properties/ActiveAlertSection';
import { getExpertSuggestions, sortAlerts } from '../components/properties/alert';
import { createRandomCoordinates, mapHouseToEntry } from '../components/properties/location';
import type { Coordinates, PropertyEntry } from '../components/properties/types';
import { useAlertNotifications } from '../components/properties/useAlertNotifications';
import { PROPERTY_ADDRESS_SAMPLES } from '../data/propertyAddressSamples';

export default function Properties() {
  const [properties, setProperties] = useState<PropertyEntry[]>([]);
  const [isLoadingProperties, setIsLoadingProperties] = useState(true);
  const [isCreatingProperty, setIsCreatingProperty] = useState(false);
  const [propertyError, setPropertyError] = useState('');
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);
  const [isAddressModalVisible, setIsAddressModalVisible] = useState(false);
  const [addressInput, setAddressInput] = useState('');
  const [showAddressSuggestions, setShowAddressSuggestions] = useState(false);
  const [addressError, setAddressError] = useState('');
  const [previewCoordinates, setPreviewCoordinates] = useState<Coordinates | null>(null);

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

  useEffect(() => {
    let isActive = true;

    const loadHouses = async () => {
      try {
        const houses = await fetchHouses();
        if (!isActive) return;
        const entries = houses.map(mapHouseToEntry);
        setProperties(entries);
        setSelectedPropertyId(entries[0]?.id ?? null);
        setPropertyError('');
      } catch (error: unknown) {
        if (!isActive) return;
        const message = error instanceof Error ? error.message : String(error);
        setPropertyError(`Couldn't load properties: ${message}`);
      } finally {
        if (isActive) setIsLoadingProperties(false);
      }
    };

    void loadHouses();
    return () => {
      isActive = false;
    };
  }, []);

  const handleAddProperty = async () => {
    const address = addressInput.trim();
    if (!address) {
      setAddressError('Enter a property address to continue.');
      return;
    }

    setIsCreatingProperty(true);
    setPropertyError('');
    try {
      const coordinates = previewCoordinates ?? createRandomCoordinates(address);
      const house = await createHouse({ address, ...coordinates });
      const newProperty = mapHouseToEntry(house);
      setProperties((currentProperties) => [
        ...currentProperties.filter((current) => current.id !== newProperty.id),
        newProperty,
      ]);
      setSelectedPropertyId(newProperty.id);
      handleCloseAddressModal();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      setPropertyError(`Couldn't create property: ${message}`);
    } finally {
      setIsCreatingProperty(false);
    }
  };

  const handleCloseAddressModal = () => {
    if (isCreatingProperty) return;
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
    <ScrollView contentContainerStyle={styles.container}>
      {/* The selector's horizontal ScrollView grows to fill free space by default.
          Wrapping it keeps it content-height so the sections sit right below it. */}
      <View style={styles.selectorWrapper}>
        <PropertySelector
          entries={properties}
          isLoading={isLoadingProperties}
          selectedId={selectedPropertyId}
          error={propertyError}
          onSelect={setSelectedPropertyId}
          onAdd={() => {
            setPropertyError('');
            setIsAddressModalVisible(true);
          }}
        />
      </View>

      <ActiveAlertSection alerts={alerts} />
      <OrderHelpSection experts={expertSuggestions} />

      <AddPropertyModal
        visible={isAddressModalVisible}
        address={addressInput}
        addressSuggestions={addressSuggestions}
        showAddressSuggestions={showAddressSuggestions}
        addressError={addressError}
        propertyError={propertyError}
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

      {/* Pushes Developer tools to the bottom when the content is short */}
      <View style={styles.spacer} />
      <DeveloperTools />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#f8fafc',
    flexGrow: 1,
  },
  selectorWrapper: {
    flexGrow: 0,
    marginBottom: 22,
  },
  spacer: {
    flexGrow: 1,
    minHeight: 16,
  },
});
