import { useRouter } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { Recipe } from "../types";
import { localized } from "../types";
import { colors } from "../theme";
import { t } from "../i18n";
import { Card, bodyText } from "./UI";
import { RecipeArtwork } from "./RecipeArtwork";

const mealKey = (meal: string) => meal === "breakfast" ? "mealBreakfast" : meal === "lunch" ? "mealLunch" : "mealDinner";

export function RecipeCard({ recipe, language = "zh" }: { recipe: Recipe; language?: string }) {
  const router = useRouter();
  const energy = recipe.nutrition?.energy_kcal;
  const sodium = recipe.sodium_table_upper_mg;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${t(language, mealKey(recipe.meal))}: ${localized(recipe.name, language)}`}
      onPress={() => router.push({ pathname: "/recipe/[id]", params: { id: recipe.recipe_id } })}
    >
      <Card style={styles.card}>
        <RecipeArtwork recipeId={recipe.image || recipe.recipe_id} language={language} />
        <View style={styles.row}>
          <Text style={styles.meal}>{t(language, mealKey(recipe.meal))}</Text>
          <Text style={styles.cost}>¥{Math.round(recipe.cost_jpy)}{t(language, "perServing")}</Text>
        </View>
        <Text style={styles.name}>{localized(recipe.name, language)}</Text>
        <Text style={bodyText.muted}>
          {recipe.minutes} 分钟 · {energy == null ? "能量数据未完整" : `${Math.round(energy)} 千卡`}
          {sodium == null ? "" : ` · 钠上界 ${Math.round(sodium)} 毫克`}
        </Text>
        {recipe.allergens?.length ? (
          <Text style={styles.allergen}>含过敏原：{recipe.allergens.join("、")}</Text>
        ) : null}
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 14, padding: 13 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 5 },
  meal: { color: colors.forest, fontSize: 12, fontWeight: "700" },
  cost: { color: colors.gold, fontSize: 12, fontWeight: "600" },
  name: { color: colors.ink, fontSize: 18, fontWeight: "700", marginBottom: 6 },
  allergen: { color: colors.danger, fontSize: 12, marginTop: 6 },
});
