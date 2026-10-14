import React, { useCallback, useEffect, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import { RecipeCard } from "../../components/RecipeCard";
import { Button, Card, LoadingBlock, Notice, PageHeading, Screen, bodyText } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { ApiError } from "../../lib/api";
import { colors, spacing } from "../../theme";
import type { HomeData, Recipe, UserProfile } from "../../types";
import { t } from "../../i18n";

export default function TodayScreen() {
  const { api, language, setLanguage } = useSession();
  const [data, setData] = useState<HomeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    return Promise.all([
        api.json<HomeData>("/home/today"),
        api.json<{ profile: UserProfile }>("/profile"),
      ]).then(([home, profile]) => {
      setError(null);
      setData(home);
      setLanguage(profile.profile.language || "zh");
    }).catch((cause: unknown) => {
      setError(cause instanceof ApiError ? cause.message : "暂时无法读取今日食谱。");
    }).finally(() => {
      setLoading(false);
      setRefreshing(false);
    });
  }, [api, setLanguage]);

  useEffect(() => { void load(); }, [load]);
  const recipes: Recipe[] = data?.personalized ? data.meals ?? [] : data?.examples ?? [];

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); void load(); }} tintColor={colors.forest} />}
      >
        <PageHeading title={t(language, "todayTitle")} subtitle={data?.date ? `${data.date} · ${language === "ja" ? "東京時間" : language === "en" ? "Tokyo time" : "东京时间"}` : t(language, "todaySubtitle")} />
        {loading ? <LoadingBlock label={t(language, "loadingToday")} /> : null}
        {error ? <Notice message={error} error /> : null}
        {!loading && !error && data && !data.personalized ? (
          <Notice message={t(language, "sampleWarning")} />
        ) : null}
        {data?.message && !data.personalized ? (
          <Card style={styles.incomplete}>
            <Text style={bodyText.section}>{t(language, "incompletePlan")}</Text>
            <Text style={bodyText.normal}>{data.message}</Text>
            <Text style={[bodyText.muted, styles.note]}>{data.note ?? t(language, "clinicalDisclaimer")}</Text>
          </Card>
        ) : null}
        {data?.personalized ? (
          <View style={styles.summary}>
            <Text style={styles.summaryLabel}>{t(language, "personalizedPlan")}</Text>
            <Text style={styles.summaryValue}>
              ¥{Math.round(data.totals?.cost_jpy ?? 0)}{t(language, "perDay")}
              {data.totals?.energy_kcal == null ? "" : `  ·  ${Math.round(data.totals.energy_kcal)} 千卡`}
            </Text>
          </View>
        ) : null}
        {recipes.map((recipe) => (
          <RecipeCard key={`${recipe.recipe_id}-${recipe.meal}`} recipe={recipe} language={language} />
        ))}
        {!loading && !error && data && recipes.length === 0 ? (
          <Card><Text style={bodyText.normal}>{t(language, "noRecipes")}</Text></Card>
        ) : null}
        <View style={styles.bottom}>
          <Button title={t(language, "refreshToday")} secondary onPress={() => { setRefreshing(true); void load(); }} />
          <Text style={styles.disclaimer}>{t(language, "todayDisclaimer")}</Text>
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.xl },
  incomplete: { backgroundColor: "#FBFCF8" },
  note: { marginTop: 9 },
  summary: { backgroundColor: colors.leaf, borderRadius: 15, padding: 15, marginBottom: 15 },
  summaryLabel: { color: colors.forest, fontSize: 13, fontWeight: "700" },
  summaryValue: { color: colors.ink, fontSize: 18, fontWeight: "700", marginTop: 5 },
  bottom: { gap: 13, marginTop: 8 },
  disclaimer: { color: colors.muted, fontSize: 11, lineHeight: 17, textAlign: "center", paddingHorizontal: 5 },
});
