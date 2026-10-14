import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { RecipeArtwork } from "../../components/RecipeArtwork";
import { Card, LoadingBlock, Notice, Screen, bodyText } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { ApiError } from "../../lib/api";
import { colors, spacing } from "../../theme";
import type { Recipe } from "../../types";
import { localized } from "../../types";
import { t } from "../../i18n";

export default function RecipeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { api, language } = useSession();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const result = await api.json<Recipe>(`/recipes/${encodeURIComponent(id)}`);
        if (mounted) {
          setRecipe(result);
        }
      } catch (cause) {
        if (mounted) setError(cause instanceof ApiError ? cause.message : "无法读取食谱详情。");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    void load();
    return () => { mounted = false; };
  }, [api, id]);

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.content}>
        <Pressable accessibilityRole="button" onPress={() => router.back()} style={styles.back}>
          <Text style={styles.backText}>{t(language, "back")}</Text>
        </Pressable>
        {loading ? <LoadingBlock label="正在读取食谱…" /> : null}
        {error ? <Notice error message={error} /> : null}
        {recipe ? (
          <>
            <Text style={styles.title}>{localized(recipe.name, language)}</Text>
            <Text style={styles.subtitle}>{recipe.minutes} · ¥{Math.round(recipe.cost_jpy)} · {t(language, "recipeImage")}</Text>
            <RecipeArtwork recipeId={recipe.image || recipe.recipe_id} language={language} />
            {recipe.allergens?.length ? <Notice error message={`${t(language, "allergyWarning")}：${recipe.allergens.join("、")}`} /> : null}
            <Card>
              <Text style={bodyText.section}>{t(language, "ingredientTitle")}</Text>
              {recipe.ingredients.map((ingredient) => (
                <View key={ingredient.code} style={styles.ingredient}>
                  <Text style={bodyText.normal}>{localized(ingredient.name, language)}</Text>
                  <Text style={bodyText.muted}>{Math.round(ingredient.grams)} 克</Text>
                </View>
              ))}
            </Card>
            <Card>
              <Text style={bodyText.section}>{t(language, "instructions")}</Text>
              <Text style={bodyText.normal}>{localized(recipe.instructions, language) || "暂无做法说明。"}</Text>
            </Card>
            <Card>
              <Text style={bodyText.section}>{t(language, "nutritionCost")}</Text>
              <Text style={bodyText.normal}>能量：{recipe.nutrition?.energy_kcal == null ? "数据不完整" : `${Math.round(recipe.nutrition.energy_kcal)} 千卡`}</Text>
              <Text style={bodyText.normal}>蛋白质：{recipe.nutrition?.protein_g == null ? "数据不完整" : `${recipe.nutrition.protein_g.toFixed(1)} 克`}</Text>
              <Text style={bodyText.normal}>钠保守上界：{recipe.sodium_table_upper_mg == null ? "数据不完整" : `${Math.round(recipe.sodium_table_upper_mg)} 毫克`}</Text>
              <Text style={[bodyText.muted, styles.note]}>{t(language, "estimatedPrice")}</Text>
            </Card>
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.xl },
  back: { paddingTop: spacing.md, paddingBottom: 12 },
  backText: { color: colors.forest, fontSize: 15, fontWeight: "700" },
  title: { color: colors.ink, fontSize: 26, fontWeight: "700" },
  subtitle: { color: colors.muted, fontSize: 13, marginTop: 7, marginBottom: 16 },
  ingredient: { flexDirection: "row", justifyContent: "space-between", borderBottomColor: colors.line, borderBottomWidth: StyleSheet.hairlineWidth, paddingVertical: 8 },
  note: { marginTop: 8 },
});
