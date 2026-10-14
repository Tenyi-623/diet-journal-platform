import { Redirect, Stack } from "expo-router";
import React from "react";

import { useSession } from "../../context/SessionContext";

export default function AuthLayout() {
  const { status } = useSession();
  if (status === "signedIn") return <Redirect href="/(tabs)" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
