import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../theme/ThemeContext';

type Task = {
  id: string;
  title: string;
  points: number;
  description: string;
};

// Starting score. Completing every task adds up to exactly 100%.
const BASE_SCORE = 77;

const INITIAL_TASKS: Task[] = [
  {
    id: 'water',
    title: 'Preventing Water Damage',
    points: 3,
    description:
      'Check if your dishwasher has a plastic leak tray underneath. It reveals hidden leaks early and ensures full compensation in case of water damage.',
  },
  {
    id: 'fire',
    title: 'Home fire safety',
    points: 3,
    description:
      'Stoves are a leading cause of home fires, and stoves must always be used under supervision. A smart stove guard cuts the power automatically in an emergency. Is your stove protected?',
  },
  {
    id: 'smoke',
    title: 'Smoke Detector Check',
    points: 3,
    description:
      'Test every smoke detector in your home by pressing the test button. Replace the batteries once a year and the whole detector every 10 years.',
  },
  {
    id: 'extinguisher',
    title: 'Fire Extinguisher Ready',
    points: 2,
    description:
      'Keep a fire extinguisher or fire blanket near the kitchen and the exit. Check that the pressure gauge is in the green zone and everyone at home knows where it is.',
  },
  {
    id: 'water-shutoff',
    title: 'Water Shut-off Valve',
    points: 3,
    description:
      'Do you know where your main water shut-off valve is? Finding it now means you can stop a burst pipe or leak within seconds instead of minutes.',
  },
  {
    id: 'washing-machine',
    title: 'Washing Machine Hoses',
    points: 2,
    description:
      'Inspect the water hoses behind your washing machine for cracks, bulges or rust on the fittings. Old rubber hoses are a common cause of flooding.',
  },
  {
    id: 'co-detector',
    title: 'Carbon Monoxide Alarm',
    points: 3,
    description:
      'Carbon monoxide is invisible and odorless. Install a CO alarm near bedrooms and fuel-burning appliances, and test it monthly.',
  },
  {
    id: 'electrical',
    title: 'Electrical Safety',
    points: 1,
    description:
      'Avoid overloading power strips and replace damaged cords. Check that chargers and heaters are never left running under blankets or on soft surfaces.',
  },
  {
    id: 'locks',
    title: 'Doors and Windows',
    points: 1,
    description:
      'Make sure all exterior doors and ground-floor windows lock properly. Consider a smart lock or door sensor for extra protection while you are away.',
  },
  {
    id: 'escape',
    title: 'Fire Escape Plan',
    points: 2,
    description:
      'Agree on two ways out of every room and a meeting point outside. Practice the plan with everyone in the household at least once a year.',
  },
];

// Red -> green segments for the index bar
const SEGMENT_COLORS = [
  '#ef4444',
  '#f2582f',
  '#f2742c',
  '#f59a2a',
  '#f5b82e',
  '#f2d12f',
  '#dbe03a',
  '#bfdc3f',
  '#9fd44a',
  '#7ccb4f',
  '#55bf4f',
  '#2fae4a',
];

export default function Info() {
  const [score, setScore] = useState(BASE_SCORE);
  const [tasks, setTasks] = useState<Task[]>(INITIAL_TASKS);
  const { colors } = useTheme();

  const completeTask = (task: Task) => {
    setScore((s) => Math.min(100, s + task.points));
    setTasks((prev) => prev.filter((t) => t.id !== task.id));
  };

  return (
    <View style={[styles.screen, { backgroundColor: colors.background }]}>
      {/* Fixed header: always visible */}
      <View
        style={[
          styles.header,
          { backgroundColor: colors.background, borderBottomColor: colors.border },
        ]}
      >
        <Text style={[styles.title, { color: colors.text }]}>Home Safety Index</Text>

        {/* Index bar */}
        <View style={styles.barWrapper}>
          <View style={styles.markerTrack}>
            <Text style={[styles.marker, { left: `${score}%`, color: colors.text }]}>▼</Text>
          </View>
          <View style={styles.barRow}>
            <View style={styles.bar}>
              {SEGMENT_COLORS.map((color, i) => (
                <View
                  key={i}
                  style={[
                    styles.segment,
                    { backgroundColor: color },
                    i < SEGMENT_COLORS.length - 1 && styles.segmentGap,
                  ]}
                />
              ))}
            </View>
            <Text style={[styles.score, { color: colors.text }]}>{score}%</Text>
          </View>
        </View>

        <Text style={[styles.intro, { color: colors.text }]}>
          The basics of your home are in order. By completing the safety challenges below, you will
          level up your home’s security and accumulate a valuable safety fund for unexpected
          situations.
        </Text>
      </View>

      {/* Scrollable task list */}
      <ScrollView
        style={styles.list}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {tasks.map((task) => (
          <View key={task.id} style={[styles.card, { backgroundColor: colors.surface }]}>
            <Text style={[styles.cardTitle, { color: colors.text }]}>
              {task.title} (+{task.points} points)
            </Text>
            <Text style={[styles.cardText, { color: colors.mutedText }]}>{task.description}</Text>
            <View style={styles.buttonRow}>
              <Pressable
                onPress={() => completeTask(task)}
                style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
              >
                <Text style={styles.buttonText}>Done</Text>
              </Pressable>
            </View>
          </View>
        ))}

        {tasks.length === 0 && (
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            <Text style={[styles.cardTitle, { color: colors.text }]}>
              All challenges completed 🎉
            </Text>
            <Text style={[styles.cardText, { color: colors.mutedText }]}>
              Great work! Your home is as safe as it gets.
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  list: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 32,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 12,
  },

  // Index bar
  barWrapper: {
    marginBottom: 16,
  },
  markerTrack: {
    // Matches bar width (score label takes ~70px on the right)
    marginRight: 70,
    height: 16,
    position: 'relative',
  },
  marker: {
    position: 'absolute',
    top: 0,
    marginLeft: -7,
    fontSize: 14,
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  bar: {
    flex: 1,
    flexDirection: 'row',
    height: 26,
    marginRight: 12,
  },
  segment: {
    flex: 1,
  },
  segmentGap: {
    marginRight: 2,
  },
  score: {
    width: 58,
    fontSize: 22,
    fontWeight: '700',
    color: '#111',
  },

  intro: {
    fontSize: 15,
    lineHeight: 21,
    marginBottom: 12,
  },

  // Task cards
  card: {
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 6,
  },
  cardText: {
    fontSize: 13,
    lineHeight: 18,
  },
  buttonRow: {
    alignItems: 'flex-end',
    marginTop: 10,
  },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 999,
    minWidth: 130,
    paddingVertical: 8,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  buttonPressed: {
    opacity: 0.8,
  },
  buttonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
});
