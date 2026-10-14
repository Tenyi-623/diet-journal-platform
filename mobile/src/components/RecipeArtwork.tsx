import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { SvgXml } from "react-native-svg";

import { useSession } from "../context/SessionContext";
import { colors } from "../theme";

export function RecipeArtwork({ recipeId, language = "zh" }: { recipeId: string; language?: string }) {
  const { api } = useSession();
  const [artwork, setArtwork] = useState<{ key: string; xml: string } | null>(null);
  const imageKey = `${recipeId}:${language}`;

  useEffect(() => {
    let current = true;
    void api.text(`/recipe-images/${encodeURIComponent(recipeId)}?lang=${language}`)
      .then((value) => { if (current && value.includes("<svg")) setArtwork({ key: imageKey, xml: value }); })
      .catch(() => undefined);
    return () => { current = false; };
  }, [api, imageKey, language, recipeId]);

  const xml = artwork?.key === imageKey ? artwork.xml : null;

  return (
    <View style={styles.frame} accessibilityLabel="食谱示意图">
      {xml ? <SvgXml xml={xml} width="100%" height="100%" /> : (
        <View style={styles.placeholder}>
          <Text style={styles.mark}>食</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { height: 142, borderRadius: 12, overflow: "hidden", backgroundColor: "#EFF2E9", marginBottom: 13 },
  placeholder: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#E8EFE3" },
  mark: { color: colors.forest, fontSize: 40, fontWeight: "700" },
});
