import React, { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { useTheme } from '../../theme/ThemeContext';
import type { Coordinates } from './types';

const MAP_ZOOM = 8;
const MAP_TILE_SIZE = 160;
const MAP_TILE_COUNT = 3;
const MAP_HEIGHT = 150;
const MAP_TILE_HEADERS = {
  'User-Agent': 'HomeGuard/1.0 (property map preview)',
};

function getTilePosition(latitude: number, longitude: number) {
  const tileCount = 2 ** MAP_ZOOM;
  const latitudeRadians = (latitude * Math.PI) / 180;
  const x = ((longitude + 180) / 360) * tileCount;
  const y = ((1 - Math.asinh(Math.tan(latitudeRadians)) / Math.PI) / 2) * tileCount;
  const tileX = Math.floor(x);
  const tileY = Math.floor(y);

  return {
    tileX,
    tileY,
    fractionX: x - tileX,
    fractionY: y - tileY,
    tileCount,
  };
}

export default function MapPreview({ coordinates }: { coordinates: Coordinates }) {
  const [mapWidth, setMapWidth] = useState(0);
  const [hasTileError, setHasTileError] = useState(false);
  const { colors } = useTheme();
  const { tileX, tileY, fractionX, fractionY, tileCount } = getTilePosition(
    coordinates.latitude,
    coordinates.longitude
  );
  const gridLeft = mapWidth / 2 - (1 + fractionX) * MAP_TILE_SIZE;
  const gridTop = MAP_HEIGHT / 2 - (1 + fractionY) * MAP_TILE_SIZE;

  return (
    <View
      style={[styles.mapFrame, { borderColor: colors.line, backgroundColor: colors.surface2 }]}
      onLayout={(event) => setMapWidth(event.nativeEvent.layout.width)}
      accessibilityLabel="Map preview showing the selected location"
    >
      {mapWidth > 0 &&
        Array.from({ length: MAP_TILE_COUNT * MAP_TILE_COUNT }, (_, index) => {
          const column = index % MAP_TILE_COUNT;
          const row = Math.floor(index / MAP_TILE_COUNT);
          const x = (((tileX + column - 1) % tileCount) + tileCount) % tileCount;
          const y = Math.max(0, Math.min(tileCount - 1, tileY + row - 1));

          return (
            <Image
              key={`${x}-${y}`}
              source={{
                uri: `https://tile.openstreetmap.org/${MAP_ZOOM}/${x}/${y}.png`,
                headers: MAP_TILE_HEADERS,
              }}
              cachePolicy="disk"
              style={[
                styles.mapTile,
                {
                  left: gridLeft + column * MAP_TILE_SIZE,
                  top: gridTop + row * MAP_TILE_SIZE,
                },
              ]}
              onError={() => setHasTileError(true)}
            />
          );
        })}
      <MaterialIcons
        name="location-on"
        size={44}
        color="#FF4A3D"
        style={styles.mapMarker}
        accessibilityLabel="Selected location marker"
      />
      {hasTileError && (
        <View style={styles.mapErrorMessage}>
          <Text style={styles.mapErrorText}>Map tiles could not be loaded.</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  mapFrame: {
    width: '100%',
    height: MAP_HEIGHT,
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 14,
    borderWidth: 1,
  },
  mapTile: {
    position: 'absolute',
    width: MAP_TILE_SIZE,
    height: MAP_TILE_SIZE,
  },
  mapMarker: {
    position: 'absolute',
    left: '50%',
    top: '50%',
    marginLeft: -22,
    marginTop: -40,
  },
  mapErrorMessage: {
    position: 'absolute',
    right: 6,
    bottom: 6,
    left: 6,
    padding: 6,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.92)',
  },
  mapErrorText: {
    color: '#b91c1c',
    fontSize: 11,
    textAlign: 'center',
  },
});
