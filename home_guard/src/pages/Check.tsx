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
import { MaterialIcons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { FONTS, useTheme } from '../theme/ThemeContext';

type Mode = 'idle' | 'camera' | 'preview';

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
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Camera frame (template) */}
      <View style={styles.frame}>
        <View
          style={[
            styles.frameContent,
            { backgroundColor: colors.surface2, borderColor: colors.line },
          ]}
        >
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
              <MaterialIcons name="photo-camera" size={64} color={colors.accentText} />
              <Text style={[styles.placeholderTitle, { color: colors.text }]}>
                Tap to open camera
              </Text>
              <Text style={[styles.placeholderHint, { color: colors.muted }]}>
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
          <Pressable
            onPress={closeCamera}
            style={styles.sideButton}
            android_ripple={{ color: colors.accentSoft, borderless: true }}
            accessibilityRole="button"
          >
            <Text style={[styles.sideButtonText, { color: colors.text }]}>Cancel</Text>
          </Pressable>
          <Pressable
            onPress={takePhoto}
            disabled={isCapturing}
            style={[
              styles.shutterOuter,
              { borderColor: colors.accent },
              isCapturing && styles.disabled,
            ]}
            accessibilityRole="button"
            accessibilityLabel="Take photo"
          >
            <View style={[styles.shutterInner, { backgroundColor: colors.accent }]} />
          </Pressable>
          <View style={styles.sideButton} />
        </View>
      )}

      {mode === 'preview' && (
        <View style={styles.actions}>
          <Pressable
            onPress={retake}
            style={styles.sideButton}
            android_ripple={{ color: colors.accentSoft, borderless: true }}
            accessibilityRole="button"
          >
            <Text style={[styles.sideButtonText, { color: colors.text }]}>Retake</Text>
          </Pressable>
          <Pressable
            onPress={confirmPhoto}
            style={({ pressed }) => [
              styles.primaryButton,
              { backgroundColor: colors.accent },
              pressed && styles.pressed,
            ]}
            accessibilityRole="button"
          >
            <Text style={[styles.primaryButtonText, { color: colors.onAccent }]}>Use photo</Text>
          </Pressable>
        </View>
      )}

      {isCapturing && <ActivityIndicator style={styles.spinner} color={colors.accentText} />}

      {permissionDenied && (
        <View style={styles.deniedBox}>
          <Text style={[styles.deniedText, { color: colors.text }]}>
            Camera access is needed to take a photo. You can enable it in the app settings.
          </Text>
          <Pressable
            onPress={() => Linking.openSettings()}
            style={({ pressed }) => [
              styles.primaryButton,
              { backgroundColor: colors.accent },
              pressed && styles.pressed,
            ]}
            accessibilityRole="button"
          >
            <Text style={[styles.primaryButtonText, { color: colors.onAccent }]}>
              Open settings
            </Text>
          </Pressable>
        </View>
      )}

      {/* Info cards */}
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}>
        <Text style={[styles.cardText, { color: colors.text }]}>
          Snap a photo of your completed safety task, such as a leak tray or a stove guard. Our AI
          instantly verifies the installation.
        </Text>
      </View>

      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}>
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
    paddingHorizontal: 18,
    paddingTop: 18,
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
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },
  placeholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
  },
  placeholderTitle: {
    fontFamily: FONTS.bodyBold,
    fontSize: 18,
  },
  placeholderHint: {
    fontFamily: FONTS.body,
    fontSize: 15,
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
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sideButtonText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 17,
  },
  primaryButton: {
    height: 52,
    minWidth: 140,
    borderRadius: 26,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.85,
  },
  primaryButtonText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 17,
  },
  shutterOuter: {
    width: 74,
    height: 74,
    borderRadius: 37,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
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
    fontFamily: FONTS.body,
    fontSize: 15,
    textAlign: 'center',
  },

  // Info cards
  card: {
    borderRadius: 18,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  },
  cardText: {
    fontFamily: FONTS.body,
    fontSize: 16,
    lineHeight: 23,
  },
});
