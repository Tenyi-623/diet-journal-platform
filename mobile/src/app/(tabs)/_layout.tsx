import { Redirect, Tabs } from "expo-router";
import React from "react";

import { LoadingBlock, Screen } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { t } from "../../i18n";
import { colors } from "../../theme";

export default function TabLayout() {
  const { status, language } = useSession();
  if (status === "loading") return <Screen><LoadingBlock /></Screen>;
  if (status !== "signedIn") return <Redirect href="/login" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.forest,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { fontSize: 12, fontWeight: "600", paddingBottom: 3 },
        tabBarStyle: { height: 62, paddingTop: 7, backgroundColor: colors.white, borderTopColor: colors.line },
      }}
    >
      <Tabs.Screen name="index" options={{ title: t(language, "today") }} />
      <Tabs.Screen name="chat" options={{ title: t(language, "chat") }} />
      <Tabs.Screen name="history" options={{ title: t(language, "history") }} />
      <Tabs.Screen name="profile" options={{ title: t(language, "profile") }} />
    </Tabs>
  );
}
