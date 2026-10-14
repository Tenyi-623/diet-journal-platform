import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewProps,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, spacing } from "../theme";

export function Screen({ children, ...props }: ViewProps) {
  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <View {...props} style={[styles.screen, props.style]}>{children}</View>
    </SafeAreaView>
  );
}

export function PageHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.heading}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

export function Card({ children, style }: ViewProps) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Button({
  title,
  onPress,
  disabled,
  secondary = false,
  loading = false,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
  loading?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled || loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        secondary && styles.buttonSecondary,
        (disabled || loading) && styles.buttonDisabled,
        pressed && !disabled && styles.buttonPressed,
      ]}
    >
      {loading ? <ActivityIndicator color={secondary ? colors.forest : colors.white} /> : (
        <Text style={[styles.buttonText, secondary && styles.buttonTextSecondary]}>{title}</Text>
      )}
    </Pressable>
  );
}

export function Field({
  label,
  hint,
  ...props
}: TextInputProps & { label: string; hint?: string }) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        style={styles.input}
        {...props}
      />
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

export function ChoiceChip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: selected }}
      onPress={onPress}
      style={[styles.chip, selected && styles.chipSelected]}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

export function Notice({ message, error = false }: { message: string; error?: boolean }) {
  return (
    <View style={[styles.notice, error && styles.noticeError]}>
      <Text style={[styles.noticeText, error && styles.noticeTextError]}>{message}</Text>
    </View>
  );
}

export function LoadingBlock({ label = "正在加载…" }: { label?: string }) {
  return (
    <View style={styles.loading}>
      <ActivityIndicator color={colors.forest} />
      <Text style={styles.loadingText}>{label}</Text>
    </View>
  );
}

export const bodyText = StyleSheet.create({
  normal: { color: colors.ink, fontSize: 15, lineHeight: 23 },
  muted: { color: colors.muted, fontSize: 13, lineHeight: 20 },
  section: { color: colors.ink, fontSize: 17, fontWeight: "700", marginBottom: 12 },
});

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.paper },
  screen: { flex: 1, backgroundColor: colors.paper, paddingHorizontal: spacing.md },
  heading: { paddingTop: spacing.md, paddingBottom: spacing.lg },
  title: { color: colors.ink, fontSize: 28, lineHeight: 34, fontWeight: "700" },
  subtitle: { color: colors.muted, marginTop: 6, fontSize: 14 },
  card: {
    backgroundColor: colors.white,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 18,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  button: {
    minHeight: 50,
    borderRadius: 14,
    backgroundColor: colors.forest,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  buttonSecondary: { backgroundColor: colors.leaf, borderWidth: 1, borderColor: colors.line },
  buttonDisabled: { opacity: 0.5 },
  buttonPressed: { opacity: 0.82 },
  buttonText: { color: colors.white, fontSize: 16, fontWeight: "700" },
  buttonTextSecondary: { color: colors.forestDark },
  fieldWrap: { gap: 7, marginBottom: spacing.md },
  label: { color: colors.ink, fontSize: 14, fontWeight: "600" },
  input: {
    color: colors.ink,
    backgroundColor: colors.input,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 12,
    minHeight: 48,
    paddingHorizontal: 13,
    fontSize: 16,
  },
  hint: { color: colors.muted, fontSize: 12, lineHeight: 18 },
  chip: {
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 99,
    paddingHorizontal: 13,
    paddingVertical: 9,
    backgroundColor: colors.white,
  },
  chipSelected: { backgroundColor: colors.leaf, borderColor: colors.forest },
  chipText: { color: colors.ink, fontSize: 13 },
  chipTextSelected: { color: colors.forestDark, fontWeight: "700" },
  notice: { backgroundColor: colors.leaf, padding: 13, borderRadius: 12, marginBottom: spacing.md },
  noticeError: { backgroundColor: colors.dangerWash },
  noticeText: { color: colors.forestDark, fontSize: 14, lineHeight: 21 },
  noticeTextError: { color: colors.danger },
  loading: { flexDirection: "row", gap: 10, alignItems: "center", justifyContent: "center", padding: spacing.lg },
  loadingText: { color: colors.muted, fontSize: 14 },
});
