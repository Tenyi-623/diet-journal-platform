import React, { useCallback, useEffect, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text } from "react-native";

import { RecipeCard } from "../../components/RecipeCard";
import { Card, LoadingBlock, Notice, PageHeading, Screen, bodyText } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { ApiError } from "../../lib/api";
import { colors, spacing } from "../../theme";
import type { Recipe } from "../../types";
import { t } from "../../i18n";

type Recommendation = {
  id: string;
  created_at: string;
  data: {
    status?: string;
    meals?: Recipe[];
    budget_jpy?: number;
    totals?: Record<string, number | null>;
    note?: string;
  };
};

export default function HistoryScreen() {
  const { api, language } = useSession();
  const [items, setItems] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    return api.json<{ recommendations: Recommendation[] }>("/recommendations").then((response) => {
      setError(null);
      setItems(response.recommendations ?? []);
    }).catch((cause: unknown) => {
      setError(cause instanceof ApiError ? cause.message : "暂时无法读取推荐历史。");
    }).finally(() => {
      setLoading(false);
      setRefreshing(false);
    });
  }, [api]);

  useEffect(() => { void load(); }, [load]);

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); void load(); }} tintColor={colors.forest} />}
      >
        <PageHeading title={t(language, "history")} subtitle={t(language, "historySubtitle")} />
        {error ? <Notice message={error} error /> : null}
        {loading ? <LoadingBlock label={t(language, "loadingHistory")} /> : null}
        {!loading && !error && items.length === 0 ? (
          <Card><Text style={bodyText.normal}>{t(language, "emptyHistory")}</Text></Card>
        ) : null}
        {items.map((item) => (
          <Card key={item.id} style={styles.planCard}>
            <Text style={styles.date}>{new Date(item.created_at).toLocaleString(language === "ja" ? "ja-JP" : language === "en" ? "en-US" : "zh-CN")}</Text>
            {item.data.budget_jpy ? <Text style={styles.budget}>{t(language, "budgetCap")} ¥{item.data.budget_jpy}{t(language, "perDay")}</Text> : null}
            {item.data.note ? <Text style={bodyText.muted}>{item.data.note}</Text> : null}
            {(item.data.meals ?? []).map((recipe) => (
              <RecipeCard key={`${item.id}-${recipe.meal}`} recipe={recipe} language={language} />
            ))}
            {!item.data.meals?.length ? <Text style={bodyText.muted}>{t(language, "noMeals")}</Text> : null}
            <Text style={styles.disclaimer}>{t(language, "demoDisclaimer")}</Text>
          </Card>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.xl },
  planCard: { padding: 14 },
  date: { color: colors.muted, fontSize: 12, marginBottom: 5 },
  budget: { color: colors.ink, fontSize: 17, fontWeight: "700", marginBottom: 10 },
  disclaimer: { color: colors.muted, fontSize: 11, lineHeight: 17, marginTop: 3 },
});
