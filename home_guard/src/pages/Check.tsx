import React, { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useTheme } from '../theme/ThemeContext';

type Mode = 'idle' | 'camera' | 'preview';

const ACCENT = '#3b4cf0';

export default function Check() {
  const { colors } = useTheme();
  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [mode, setMode] = useState<Mode>('idle');
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);

  const openCamera = async () => {
    if (!permission?.granted) {
      const result = await requestPermission();
      if (!result.granted) {
        setPermissionDenied(true);
        return;
      }
    }
    setPermissionDenied(false);
    setPhotoUri(null);
    setMode('camera');
  };

  const closeCamera = () => {
    setMode('idle');
    setPhotoUri(null);
  };

  const takePhoto = async () => {
    if (isCapturing) return;
    setIsCapturing(true);
    try {
      const photo = await cameraRef.current?.takePictureAsync({ quality: 0.7 });
      if (photo?.uri) {
        setPhotoUri(photo.uri);
        setMode('preview');
      }
    } finally {
      setIsCapturing(false);
    }
  };

  const retake = () => {
    setPhotoUri(null);
    setMode('camera');
  };

  const confirmPhoto = () => {
    if (!photoUri) return;
    // TODO: send `photoUri` to your AI verification backend here.
    console.log('Photo ready for verification:', photoUri);
    closeCamera();
  };

  // Corner brackets are dark on the idle placeholder and white over the camera / photo.
  const bracketColor = mode === 'idle' ? colors.text : '#ffffff';

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Camera frame (template) */}
      <View style={styles.frame}>
        <View style={styles.frameContent}>
          {mode === 'camera' && (
            <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
          )}

          {mode === 'preview' && photoUri && (
            <Image source={{ uri: photoUri }} style={StyleSheet.absoluteFill} />
          )}

          {mode === 'idle' && (
            <Pressable
              style={styles.placeholder}
              onPress={openCamera}
              accessibilityRole="button"
              accessibilityLabel="Open camera"
            >
              <Ionicons name="camera-outline" size={64} color={colors.text} />
              <Text style={[styles.placeholderTitle, { color: colors.text }]}>
                Tap to open camera
              </Text>
              <Text style={[styles.placeholderHint, { color: colors.mutedText }]}>
                Photograph your completed safety task
              </Text>
            </Pressable>
          )}
        </View>

        {/* Viewfinder corners */}
        <View
          pointerEvents="none"
          style={[styles.corner, styles.topLeft, { borderColor: bracketColor }]}
        />
        <View
          pointerEvents="none"
          style={[styles.corner, styles.topRight, { borderColor: bracketColor }]}
        />
        <View
          pointerEvents="none"
          style={[styles.corner, styles.bottomLeft, { borderColor: bracketColor }]}
        />
        <View
          pointerEvents="none"
          style={[styles.corner, styles.bottomRight, { borderColor: bracketColor }]}
        />
      </View>

      {/* Camera controls */}
      {mode === 'camera' && (
        <View style={styles.actions}>
          <Pressable onPress={closeCamera} style={styles.sideButton}>
            <Text style={[styles.sideButtonText, { color: colors.text }]}>Cancel</Text>
          </Pressable>
          <Pressable
            onPress={takePhoto}
            disabled={isCapturing}
            style={[styles.shutterOuter, isCapturing && styles.disabled]}
            accessibilityRole="button"
            accessibilityLabel="Take photo"
          >
            <View style={styles.shutterInner} />
          </Pressable>
          <View style={styles.sideButton} />
        </View>
      )}

      {mode === 'preview' && (
        <View style={styles.actions}>
          <Pressable onPress={retake} style={styles.sideButton}>
            <Text style={[styles.sideButtonText, { color: colors.text }]}>Retake</Text>
          </Pressable>
          <Pressable onPress={confirmPhoto} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Use photo</Text>
          </Pressable>
        </View>
      )}

      {isCapturing && <ActivityIndicator style={styles.spinner} color={ACCENT} />}

      {permissionDenied && (
        <View style={styles.deniedBox}>
          <Text style={[styles.deniedText, { color: colors.text }]}>
            Camera access is needed to take a photo. You can enable it in the app settings.
          </Text>
          <Pressable onPress={() => Linking.openSettings()} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Open settings</Text>
          </Pressable>
        </View>
      )}

      {/* Info cards */}
      <View style={styles.card}>
        <Text style={[styles.cardText, { color: colors.text }]}>
          Snap a photo of your completed safety task, such as a leak tray or a stove guard. Our AI
          instantly verifies the installation.
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.cardText, { color: colors.text }]}>
          “Did I lock the door? Is the stove off?” Take a quick photo before you leave. Our AI
          confirms everything is secure, saving a time-stamped status you can check anywhere,
          anytime.
        </Text>
      </View>
    </ScrollView>
  );
}

const CORNER_SIZE = 40;
const CORNER_WIDTH = 4;

const styles = StyleSheet.create({
  content: {
    padding: 20,
    paddingBottom: 32,
  },

  // Frame
  frame: {
    width: '100%',
    aspectRatio: 4 / 3,
    marginBottom: 20,
  },
  frameContent: {
    position: 'absolute',
    top: 10,
    left: 10,
    right: 10,
    bottom: 10,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: 'rgba(120,120,120,0.08)',
  },
  placeholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
  },
  placeholderTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  placeholderHint: {
    fontSize: 13,
    textAlign: 'center',
  },
  corner: {
    position: 'absolute',
    width: CORNER_SIZE,
    height: CORNER_SIZE,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: CORNER_WIDTH,
    borderLeftWidth: CORNER_WIDTH,
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: CORNER_WIDTH,
    borderRightWidth: CORNER_WIDTH,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: CORNER_WIDTH,
    borderLeftWidth: CORNER_WIDTH,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: CORNER_WIDTH,
    borderRightWidth: CORNER_WIDTH,
  },

  // Controls
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  sideButton: {
    width: 90,
    paddingVertical: 10,
    alignItems: 'center',
  },
  sideButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  primaryButton: {
    backgroundColor: ACCENT,
    borderRadius: 999,
    minWidth: 130,
    paddingVertical: 10,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },
  shutterOuter: {
    width: 74,
    height: 74,
    borderRadius: 37,
    borderWidth: 4,
    borderColor: ACCENT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: ACCENT,
  },
  disabled: {
    opacity: 0.5,
  },
  spinner: {
    marginBottom: 16,
  },
  deniedBox: {
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
  },
  deniedText: {
    fontSize: 14,
    textAlign: 'center',
  },

  // Info cards
  card: {
    backgroundColor: 'rgba(120,120,120,0.08)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 14,
  },
  cardText: {
    fontSize: 15,
    lineHeight: 22,
  },
});
