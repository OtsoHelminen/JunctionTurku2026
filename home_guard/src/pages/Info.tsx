import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { FONTS, useTheme } from '../theme/ThemeContext';

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
  '#E5484D',
  '#EE5A35',
  '#F2742B',
  '#F5952A',
  '#F6B52B',
  '#EECF2E',
  '#D9DE34',
  '#B9DB3C',
  '#97D145',
  '#77C84C',
  '#5DBF4F',
  '#34A853',
];

export default function Info() {
  const [score, setScore] = useState(BASE_SCORE);
  const [tasks, setTasks] = useState<Task[]>(INITIAL_TASKS);
  const { colors } = useTheme();
  // The marker sits above the segment the score falls into (77% -> 10th of 12)
  const markerIndex = Math.max(1, Math.ceil((score / 100) * SEGMENT_COLORS.length)) - 1;

  const completeTask = (task: Task) => {
    setScore((s) => Math.min(100, s + task.points));
    setTasks((prev) => prev.filter((t) => t.id !== task.id));
  };

  return (
    <View style={[styles.screen, { backgroundColor: colors.bg }]}>
      {/* Fixed header: always visible */}
      <View style={[styles.header, { borderBottomColor: colors.line }]}>
        <Text style={[styles.title, { color: colors.text }]} accessibilityRole="header">
          Home Safety Index
        </Text>

        {/* Index bar */}
        <View
          style={styles.barRow}
          accessible
          accessibilityLabel={`Home Safety Index ${score} percent`}
        >
          <View style={styles.barColumn}>
            <View style={styles.segmentRow}>
              {SEGMENT_COLORS.map((color, i) => (
                <Text key={color} style={[styles.marker, { color: colors.text }]}>
                  {i === markerIndex ? '▼' : ''}
                </Text>
              ))}
            </View>
            <View style={[styles.segmentRow, styles.bar]}>
              {SEGMENT_COLORS.map((color) => (
                <View key={color} style={[styles.segment, { backgroundColor: color }]} />
              ))}
            </View>
          </View>
          <Text style={[styles.score, { color: colors.text }]}>{score}%</Text>
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
          <View
            key={task.id}
            style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}
          >
            <Text style={[styles.cardTitle, { color: colors.text }]}>
              {task.title} (+{task.points} points)
            </Text>
            <Text style={[styles.cardText, { color: colors.muted }]}>{task.description}</Text>
            <View style={styles.buttonRow}>
              <Pressable
                onPress={() => completeTask(task)}
                style={({ pressed }) => [
                  styles.button,
                  { backgroundColor: colors.accent },
                  pressed && styles.buttonPressed,
                ]}
                accessibilityRole="button"
                accessibilityLabel={`Mark ${task.title} done`}
              >
                <Text style={[styles.buttonText, { color: colors.onAccent }]}>Done</Text>
              </Pressable>
            </View>
          </View>
        ))}

        {tasks.length === 0 && (
          <View
            style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}
          >
            <Text style={[styles.cardTitle, { color: colors.text }]}>
              All challenges completed 🎉
            </Text>
            <Text style={[styles.cardText, { color: colors.muted }]}>
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
    paddingHorizontal: 18,
    paddingTop: 20,
    paddingBottom: 18,
    gap: 14,
    borderBottomWidth: 1,
  },
  list: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 18,
    paddingVertical: 16,
    gap: 12,
  },
  title: {
    fontFamily: FONTS.heading,
    fontSize: 24,
  },

  // Index bar
  barRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 12,
  },
  barColumn: {
    flex: 1,
    gap: 4,
  },
  segmentRow: {
    flexDirection: 'row',
    gap: 3,
  },
  bar: {
    height: 22,
  },
  segment: {
    flex: 1,
    borderRadius: 4,
  },
  marker: {
    flex: 1,
    fontSize: 14,
    lineHeight: 14,
    textAlign: 'center',
  },
  score: {
    fontFamily: FONTS.heading,
    fontSize: 28,
    lineHeight: 28,
  },

  intro: {
    fontFamily: FONTS.body,
    fontSize: 16,
    lineHeight: 23,
  },

  // Task cards
  card: {
    borderRadius: 18,
    borderWidth: 1,
    padding: 16,
    gap: 8,
  },
  cardTitle: {
    fontFamily: FONTS.bodyBold,
    fontSize: 17,
    lineHeight: 21,
  },
  cardText: {
    fontFamily: FONTS.body,
    fontSize: 15,
    lineHeight: 21,
  },
  buttonRow: {
    alignItems: 'flex-end',
  },
  button: {
    width: 140,
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
