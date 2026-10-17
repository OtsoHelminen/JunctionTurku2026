import React, { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { createHouse, fetchHouses } from '../api/houses';
import AddRealEstateModal from '../components/realEstate/AddRealEstateModal';
import DeveloperTools from '../components/realEstate/DeveloperTools';
import OrderHelpSection from '../components/realEstate/OrderHelpSection';
import RealEstateSelector from '../components/realEstate/RealEstateSelector';
import WarningsSection from '../components/realEstate/WarningsSection';
import { getExpertSuggestions, sortAlerts } from '../components/realEstate/alert';
import { createRandomCoordinates, mapHouseToEntry } from '../components/realEstate/location';
import type { Coordinates, RealEstateEntry } from '../components/realEstate/types';
import { useAlertNotifications } from '../components/realEstate/useAlertNotifications';
import { REAL_ESTATE_ADDRESS_SAMPLES } from '../data/realEstateAddressSamples';

export default function RealEstate() {
  const [realEstates, setRealEstates] = useState<RealEstateEntry[]>([]);
  const [isLoadingRealEstates, setIsLoadingRealEstates] = useState(true);
  const [isCreatingRealEstate, setIsCreatingRealEstate] = useState(false);
  const [realEstateError, setRealEstateError] = useState('');
  const [selectedRealEstateId, setSelectedRealEstateId] = useState<number | null>(null);
  const [isAddressModalVisible, setIsAddressModalVisible] = useState(false);
  const [addressInput, setAddressInput] = useState('');
  const [showAddressSuggestions, setShowAddressSuggestions] = useState(false);
  const [addressError, setAddressError] = useState('');
  const [previewCoordinates, setPreviewCoordinates] = useState<Coordinates | null>(null);

  const allAlerts = useAlertNotifications();

  // Only the selected real estate's alerts, most urgent first
  const alerts = useMemo(
    () =>
      sortAlerts(
        allAlerts.filter(
          (alert) =>
            selectedRealEstateId === null ||
            alert.houseId === null ||
            alert.houseId === selectedRealEstateId
        )
      ),
    [allAlerts, selectedRealEstateId]
  );
  const expertSuggestions = useMemo(() => getExpertSuggestions(alerts), [alerts]);

  const addressSuggestions =
    showAddressSuggestions && addressInput.trim().length >= 2
      ? REAL_ESTATE_ADDRESS_SAMPLES.filter((address) =>
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
        setRealEstates(entries);
        setSelectedRealEstateId(entries[0]?.id ?? null);
        setRealEstateError('');
      } catch (error: unknown) {
        if (!isActive) return;
        const message = error instanceof Error ? error.message : String(error);
        setRealEstateError(`Couldn't load real estates: ${message}`);
      } finally {
        if (isActive) setIsLoadingRealEstates(false);
      }
    };

    void loadHouses();
    return () => {
      isActive = false;
    };
  }, []);

  const handleAddRealEstate = async () => {
    const address = addressInput.trim();
    if (!address) {
      setAddressError('Enter a real estate address to continue.');
      return;
    }

    setIsCreatingRealEstate(true);
    setRealEstateError('');
    try {
      const coordinates = previewCoordinates ?? createRandomCoordinates(address);
      const house = await createHouse({ address, ...coordinates });
      const newRealEstate = mapHouseToEntry(house);
      setRealEstates((currentRealEstates) => [
        ...currentRealEstates.filter((current) => current.id !== newRealEstate.id),
        newRealEstate,
      ]);
      setSelectedRealEstateId(newRealEstate.id);
      handleCloseAddressModal();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      setRealEstateError(`Couldn't create real estate: ${message}`);
    } finally {
      setIsCreatingRealEstate(false);
    }
  };

  const handleCloseAddressModal = () => {
    if (isCreatingRealEstate) return;
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
      <RealEstateSelector
        entries={realEstates}
        isLoading={isLoadingRealEstates}
        selectedId={selectedRealEstateId}
        error={realEstateError}
        onSelect={setSelectedRealEstateId}
        onAdd={() => {
          setRealEstateError('');
          setIsAddressModalVisible(true);
        }}
      />

      <WarningsSection alerts={alerts} />
      <OrderHelpSection experts={expertSuggestions} />

      <AddRealEstateModal
        visible={isAddressModalVisible}
        address={addressInput}
        addressSuggestions={addressSuggestions}
        showAddressSuggestions={showAddressSuggestions}
        addressError={addressError}
        realEstateError={realEstateError}
        previewCoordinates={previewCoordinates}
        isCreating={isCreatingRealEstate}
        onClose={handleCloseAddressModal}
        onAdd={handleAddRealEstate}
        onAddressChange={(value) => {
          setAddressInput(value);
          setShowAddressSuggestions(true);
          setPreviewCoordinates(null);
          if (addressError) setAddressError('');
        }}
        onAddressFocus={() => setShowAddressSuggestions(true)}
        onSelectAddressSuggestion={handleSelectAddressSuggestion}
      />

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
});
