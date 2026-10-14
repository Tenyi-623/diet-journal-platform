import { Redirect } from "expo-router";
import React from "react";

import { LoadingBlock, Screen } from "../components/UI";
import { useSession } from "../context/SessionContext";

export default function IndexRoute() {
  const { status, error } = useSession();
  if (status === "loading") {
    return <Screen><LoadingBlock label="正在检查登录状态…" /></Screen>;
  }
  if (status === "signedIn") return <Redirect href="/(tabs)" />;
  if (status === "unavailable") {
    return <Redirect href={{ pathname: "/login", params: { retry: "1", reason: error ?? "" } }} />;
  }
  return <Redirect href="/login" />;
}
