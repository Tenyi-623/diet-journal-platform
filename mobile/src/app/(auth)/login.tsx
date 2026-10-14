import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { Button, Card, Field, Notice, Screen } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { ApiError } from "../../lib/api";
import { colors, spacing } from "../../theme";
import { t } from "../../i18n";

export default function LoginScreen() {
  const { api, error: sessionError, language, login, retrySession, status } = useSession();
  const params = useLocalSearchParams<{ retry?: string; reason?: string }>();
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.retry === "1") void retrySession();
  }, [params.retry, retrySession]);

  useEffect(() => {
    if (status === "signedIn") router.replace("/(tabs)");
  }, [router, status]);

  async function submit() {
    if (!loginId.trim() || !password) {
      setError("请输入登录 ID 和密码。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(loginId.trim(), password);
      router.replace("/(tabs)");
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        setError("登录 ID 或密码不正确。");
      } else if (cause instanceof ApiError && cause.status === 429) {
        setError("尝试次数过多，请稍后再试。");
      } else {
        setError(cause instanceof Error ? cause.message : "登录失败，请稍后重试。");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <KeyboardAvoidingView
        style={styles.keyboard}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={styles.brandMark}><Text style={styles.leaf}>✦</Text></View>
          <Text style={styles.brand}>食日记</Text>
          <Text style={styles.brandEn}>DIET JOURNAL</Text>
          <Text style={styles.title}>{t(language, "loginTitle")}</Text>
          <Text style={styles.subtitle}>{t(language, "loginSubtitle")}</Text>

          <Card style={styles.form}>
            {api.configurationError ? <Notice error message={api.configurationError} /> : null}
            {sessionError ? <Notice error message={sessionError} /> : null}
            {params.reason ? <Notice error message={String(params.reason)} /> : null}
            {error ? <Notice error message={error} /> : null}
            <Field
              label={t(language, "loginId")}
              placeholder={t(language, "loginIdPlaceholder")}
              value={loginId}
              onChangeText={setLoginId}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              textContentType="username"
            />
            <Field
              label={t(language, "password")}
              placeholder={t(language, "passwordPlaceholder")}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              textContentType="password"
              returnKeyType="go"
              onSubmitEditing={() => void submit()}
            />
            <Button title={t(language, "login")} onPress={() => void submit()} loading={busy} disabled={!!api.configurationError} />
            <Text style={styles.noRegistration}>{t(language, "noRegistration")}</Text>
          </Card>
          {status === "unavailable" ? (
            <Button title="重新连接" secondary onPress={() => void retrySession()} />
          ) : null}
          <Text style={styles.footer}>{t(language, "loginFooter")}</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  keyboard: { flex: 1 },
  content: { flexGrow: 1, justifyContent: "center", paddingTop: spacing.xl, paddingBottom: spacing.xl },
  brandMark: { width: 54, height: 54, borderRadius: 27, backgroundColor: colors.forest, alignItems: "center", justifyContent: "center", marginBottom: 10 },
  leaf: { color: colors.white, fontSize: 25 },
  brand: { color: colors.ink, fontSize: 26, fontWeight: "800", letterSpacing: 1 },
  brandEn: { color: colors.forest, fontSize: 10, fontWeight: "800", letterSpacing: 3, marginTop: 2 },
  title: { color: colors.ink, fontSize: 27, fontWeight: "700", marginTop: 38 },
  subtitle: { color: colors.muted, fontSize: 14, marginTop: 7, marginBottom: 18 },
  form: { padding: spacing.lg },
  noRegistration: { color: colors.muted, fontSize: 12, lineHeight: 18, textAlign: "center", marginTop: 13 },
  footer: { color: colors.muted, fontSize: 12, textAlign: "center", marginTop: spacing.lg },
});
