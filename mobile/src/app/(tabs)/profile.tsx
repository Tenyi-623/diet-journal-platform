import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { Button, Card, ChoiceChip, Field, LoadingBlock, Notice, PageHeading, Screen, bodyText } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { ApiError } from "../../lib/api";
import { bloodPressureRecordFromCreate, type BPRecord } from "../../lib/bloodPressure";
import { colors, spacing } from "../../theme";
import type { IncomeBand, Language, UserProfile } from "../../types";
import { localized } from "../../types";
import { t } from "../../i18n";

type ProfileResponse = { version: number; profile: UserProfile };
type Food = { code: string; name: string | Record<string, string>; allergens?: string[] };
const allergyChoices: [string, string][] = [
  ["milk", "milk"], ["egg", "egg"], ["soy", "soy"], ["wheat", "wheat"],
  ["fish", "fish"], ["nuts", "nuts"], ["other", "otherAllergen"],
];
const conditionChoices: [string, string][] = [
  ["hypertension", "hypertension"], ["diabetes", "diabetes"], ["kidney", "kidney"],
  ["pregnancy", "pregnancy"], ["other", "otherCondition"],
];
const languages: [Language, string][] = [["zh", "中文"], ["en", "English"], ["ja", "日本語"]];
const parseNullableNumber = (value: string) => value.trim() ? Number(value) : null;

export default function ProfileScreen() {
  const { api, logout, setLanguage, user } = useSession();
  const [version, setVersion] = useState(0);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [bands, setBands] = useState<IncomeBand[]>([]);
  const [foods, setFoods] = useState<Food[]>([]);
  const [foodQuery, setFoodQuery] = useState("");
  const [records, setRecords] = useState<BPRecord[]>([]);
  const [systolic, setSystolic] = useState("");
  const [diastolic, setDiastolic] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(() => {
    return Promise.all([
        api.json<ProfileResponse>("/profile"),
        api.json<{ bands: IncomeBand[] }>("/income-bands"),
        api.json<{ foods: Food[] }>("/foods"),
        api.json<{ records: BPRecord[] }>("/blood-pressure"),
      ]).then(([profileResult, incomeResult, foodResult, bpResult]) => {
      setError(null);
      setVersion(profileResult.version);
      setProfile({ ...profileResult.profile, expected_version: profileResult.version });
      setBands(incomeResult.bands ?? []);
      setFoods(foodResult.foods ?? []);
      setRecords(bpResult.records ?? []);
    }).catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : "无法读取用户信息。");
    }).finally(() => {
      setLoading(false);
    });
  }, [api]);

  useEffect(() => { void load(); }, [load]);

  const selectedBand = useMemo(
    () => bands.find((band) => band.id === profile?.income_band),
    [bands, profile?.income_band],
  );

  function update<K extends keyof UserProfile>(key: K, value: UserProfile[K]) {
    setProfile((current) => current ? { ...current, [key]: value } : current);
    setSaved(false);
  }

  function toggleList(key: "allergens" | "conditions" | "dislikes", value: string) {
    if (!profile) return;
    const current = profile[key];
    update(key, (current.includes(value) ? current.filter((item) => item !== value) : [...current, value]) as UserProfile[typeof key]);
  }

  async function saveProfile() {
    if (!profile) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const result = await api.json<ProfileResponse>("/profile", {
        method: "PATCH",
        body: JSON.stringify({ ...profile, expected_version: version }),
      });
      setVersion(result.version);
      setProfile({ ...result.profile, expected_version: result.version });
      setLanguage(result.profile.language);
      setSaved(true);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        setError("用户信息已在其他位置更新。为避免覆盖，请刷新后重新确认。");
      } else {
        setError(cause instanceof Error ? cause.message : "保存失败，请检查填写内容。 ");
      }
    } finally {
      setSaving(false);
    }
  }

  async function searchFoods() {
    try {
      const result = await api.json<{ foods: Food[] }>(`/foods?q=${encodeURIComponent(foodQuery.trim())}`);
      setFoods(result.foods ?? []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "食品目录暂时无法读取。");
    }
  }

  async function addBP() {
    const high = Number(systolic);
    const low = Number(diastolic);
    const measurement = {
      systolic: high,
      diastolic: low,
      measured_at: new Date().toISOString(),
    };
    try {
      const result = await api.json<{ id: number; note: string }>("/blood-pressure", {
        method: "POST",
        body: JSON.stringify(measurement),
      });
      const record = bloodPressureRecordFromCreate(result, measurement);
      setRecords((current) => [record, ...current]);
      setSystolic("");
      setDiastolic("");
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "血压记录未保存，请检查数值。 ");
    }
  }

  async function changePassword() {
    if (newPassword.length < 12) {
      setError("新密码至少需要 12 个字符。");
      return;
    }
    try {
      await api.json("/auth/password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      setCurrentPassword("");
      setNewPassword("");
      await logout();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "密码更新失败，请检查当前密码。 ");
    }
  }

  function confirmLogout() {
    Alert.alert(t(profile?.language ?? "zh", "logout"), t(profile?.language ?? "zh", "logoutConfirm"), [
      { text: t(profile?.language ?? "zh", "cancelLabel"), style: "cancel" },
      { text: t(profile?.language ?? "zh", "confirmLogout"), style: "destructive", onPress: () => { void logout(); } },
    ]);
  }

  if (loading) return <Screen><LoadingBlock label="正在读取用户信息…" /></Screen>;
  if (!profile) {
    return <Screen><PageHeading title="用户信息" /><Notice error message={error ?? "用户信息暂不可用。"} /><Button title="重新加载" onPress={() => { setLoading(true); void load(); }} /></Screen>;
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <PageHeading title={t(profile.language, "profile")} subtitle={`${t(profile.language, "profileSubtitle")} ${user?.login_id ?? ""} · ${t(profile.language, "personalOnly")}`} />
        {error ? <Notice message={error} error /> : null}
        {saved ? <Notice message={t(profile.language, "saved")} /> : null}

        <Card>
          <Text style={bodyText.section}>{t(profile.language, "basicIncome")}</Text>
          <Field label={t(profile.language, "displayName")} value={profile.display_name} onChangeText={(value) => update("display_name", value)} maxLength={40} />
          <Field label={t(profile.language, "age")} value={profile.age == null ? "" : String(profile.age)} onChangeText={(value) => update("age", parseNullableNumber(value))} keyboardType="number-pad" placeholder={t(profile.language, "age")} />
          <View style={styles.twoColumns}>
            <Field label={t(profile.language, "height")} value={profile.height_cm == null ? "" : String(profile.height_cm)} onChangeText={(value) => update("height_cm", parseNullableNumber(value))} keyboardType="decimal-pad" />
            <Field label={t(profile.language, "weight")} value={profile.weight_kg == null ? "" : String(profile.weight_kg)} onChangeText={(value) => update("weight_kg", parseNullableNumber(value))} keyboardType="decimal-pad" />
          </View>
          <Text style={styles.label}>{t(profile.language, "annualIncome")}</Text>
          <View style={styles.chips}>
            {bands.map((band) => (
              <ChoiceChip key={band.id} label={band.label} selected={profile.income_band === band.id} onPress={() => update("income_band", band.id)} />
            ))}
          </View>
          {selectedBand ? <Notice message={profile.language === "en" ? `Demo budget for this income band: ¥${selectedBand.daily_budget} per day. This is synthetic and is not a disposable-income estimate.` : profile.language === "ja" ? `この年収区分のデモ予算は ¥${selectedBand.daily_budget} / 日です。可処分所得の推定ではありません。` : `该收入档次对应的演示预算为 ¥${selectedBand.daily_budget} / 日。它是合成演示配置，不是可支配收入测算。`} /> : <Notice error message={profile.language === "en" ? "Select an annual income band to use the demo budget rule." : profile.language === "ja" ? "デモの予算ルールを使うには年収区分を選択してください。" : "请选择年收入档次，系统才能按演示规则估算预算。"} />}
          <Field label={t(profile.language, "customBudget")} value={profile.daily_budget == null ? "" : String(profile.daily_budget)} onChangeText={(value) => update("daily_budget", parseNullableNumber(value))} keyboardType="number-pad" placeholder={selectedBand ? `¥${selectedBand.daily_budget}${t(profile.language, "perDay")}` : "100–20000"} />
          <Text style={styles.label}>{t(profile.language, "language")}</Text>
          <View style={styles.chips}>
            {languages.map(([code, label]) => <ChoiceChip key={code} label={label} selected={profile.language === code} onPress={() => update("language", code)} />)}
          </View>
        </Card>

        <Card>
          <Text style={bodyText.section}>{t(profile.language, "healthAllergy")}</Text>
          <Text style={styles.label}>{t(profile.language, "allergyStatus")}</Text>
          <View style={styles.chips}>
            {([["unknown", "unconfirmed"], ["none", "noAllergy"], ["present", "hasAllergy"]] as const).map(([value, label]) => (
              <ChoiceChip key={value} label={t(profile.language, label)} selected={profile.allergy_status === value} onPress={() => {
                update("allergy_status", value);
                if (value !== "present") update("allergens", []);
              }} />
            ))}
          </View>
          {profile.allergy_status === "present" ? (
            <>
              <Text style={styles.label}>{t(profile.language, "confirmedAllergens")}</Text>
              <View style={styles.chips}>
                {allergyChoices.map(([code, label]) => <ChoiceChip key={code} label={t(profile.language, label)} selected={profile.allergens.includes(code)} onPress={() => toggleList("allergens", code)} />)}
              </View>
            </>
          ) : null}
          <Text style={styles.label}>{t(profile.language, "healthConditions")}</Text>
          <View style={styles.chips}>
            {conditionChoices.map(([code, label]) => <ChoiceChip key={code} label={t(profile.language, label)} selected={profile.conditions.includes(code)} onPress={() => toggleList("conditions", code)} />)}
          </View>
          <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: profile.health_confirmed }} onPress={() => update("health_confirmed", !profile.health_confirmed)} style={styles.checkRow}>
            <Text style={[styles.checkbox, profile.health_confirmed && styles.checkboxSelected]}>{profile.health_confirmed ? "✓" : ""}</Text>
            <Text style={bodyText.normal}>{t(profile.language, "healthConfirmed")}</Text>
          </Pressable>
          <Notice message={t(profile.language, "bpDisclaimer")} />
        </Card>

        <Card>
          <Text style={bodyText.section}>{t(profile.language, "preferences")}</Text>
          <Text style={styles.label}>{t(profile.language, "dietPreference")}</Text>
          <View style={styles.chips}>
            <ChoiceChip label={t(profile.language, "anyDiet")} selected={profile.diet === "any"} onPress={() => update("diet", "any")} />
            <ChoiceChip label={t(profile.language, "vegetarian")} selected={profile.diet === "vegetarian"} onPress={() => update("diet", "vegetarian")} />
          </View>
          <Field label={t(profile.language, "cookingTime")} value={String(profile.cooking_minutes)} onChangeText={(value) => update("cooking_minutes", Number(value))} keyboardType="number-pad" />
          <Text style={styles.label}>{t(profile.language, "dislikedFoods")}</Text>
          <View style={styles.searchRow}>
            <View style={styles.searchInput}><Field label={t(profile.language, "foodSearch")} value={foodQuery} onChangeText={setFoodQuery} placeholder={t(profile.language, "foodPlaceholder")} /></View>
            <View style={styles.searchButton}><Button title={t(profile.language, "search")} onPress={() => void searchFoods()} secondary /></View>
          </View>
          {profile.dislikes.length ? (
            <View style={styles.chips}>
              {profile.dislikes.map((code) => {
                const food = foods.find((item) => item.code === code);
                return <ChoiceChip key={code} label={food ? localized(food.name, profile.language) : code} selected onPress={() => toggleList("dislikes", code)} />;
              })}
            </View>
          ) : <Text style={bodyText.muted}>{t(profile.language, "noDislikes")}</Text>}
          <View style={styles.chips}>
            {foods.map((food) => (
              <ChoiceChip key={food.code} label={localized(food.name, profile.language)} selected={profile.dislikes.includes(food.code)} onPress={() => toggleList("dislikes", food.code)} />
            ))}
          </View>
        </Card>

        <Card>
          <Text style={bodyText.section}>{t(profile.language, "demoSettings")}</Text>
          <Field label={t(profile.language, "energyGoal")} value={String(profile.energy_kcal)} onChangeText={(value) => update("energy_kcal", Number(value))} keyboardType="number-pad" />
          <Field label={t(profile.language, "sodiumLimit")} value={String(profile.sodium_max_mg)} onChangeText={(value) => update("sodium_max_mg", Number(value))} keyboardType="number-pad" />
          <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: profile.demo_consent }} onPress={() => update("demo_consent", !profile.demo_consent)} style={styles.checkRow}>
            <Text style={[styles.checkbox, profile.demo_consent && styles.checkboxSelected]}>{profile.demo_consent ? "✓" : ""}</Text>
            <Text style={bodyText.normal}>{t(profile.language, "demoConsent")}</Text>
          </Pressable>
          <Notice message={t(profile.language, "clinicalDisclaimer")} />
          <Button title={t(profile.language, "saveProfile")} onPress={() => void saveProfile()} loading={saving} />
          <View style={styles.reload}><Button title={t(profile.language, "reload")} onPress={() => { setLoading(true); void load(); }} secondary /></View>
        </Card>

        <Card>
          <Text style={bodyText.section}>{t(profile.language, "bpRecords")}</Text>
          <Text style={bodyText.muted}>{t(profile.language, "bpRecordHint")}</Text>
          <View style={styles.twoColumns}>
            <Field label={t(profile.language, "systolic")} value={systolic} onChangeText={setSystolic} keyboardType="number-pad" placeholder="120" />
            <Field label={t(profile.language, "diastolic")} value={diastolic} onChangeText={setDiastolic} keyboardType="number-pad" placeholder="80" />
          </View>
          <Button title={t(profile.language, "addBP")} onPress={() => void addBP()} disabled={!systolic || !diastolic} />
          {records.slice(0, 8).map((record) => (
            <View key={record.id} style={styles.bpRow}>
              <Text style={bodyText.normal}>{record.systolic} / {record.diastolic} mmHg</Text>
              <Text style={bodyText.muted}>{new Date(record.measured_at).toLocaleString()}</Text>
            </View>
          ))}
          {!records.length ? <Text style={[bodyText.muted, styles.empty]}>{t(profile.language, "noBP")}</Text> : null}
        </Card>

        <Card>
          <Text style={bodyText.section}>{t(profile.language, "changePassword")}</Text>
          <Field label={t(profile.language, "currentPassword")} value={currentPassword} onChangeText={setCurrentPassword} secureTextEntry />
          <Field label={t(profile.language, "newPassword")} value={newPassword} onChangeText={setNewPassword} secureTextEntry />
          <Button title={t(profile.language, "changePasswordLogout")} onPress={() => void changePassword()} secondary disabled={!currentPassword || !newPassword} />
        </Card>

        <View style={styles.logout}><Button title={t(profile.language, "logout")} onPress={confirmLogout} secondary /></View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.xl },
  label: { color: colors.ink, fontSize: 14, fontWeight: "600", marginBottom: 9 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: spacing.md },
  twoColumns: { flexDirection: "row", gap: 10 },
  checkRow: { flexDirection: "row", gap: 10, alignItems: "center", marginVertical: 9 },
  checkbox: { width: 22, height: 22, borderRadius: 5, borderWidth: 1, borderColor: colors.muted, textAlign: "center", textAlignVertical: "center", color: colors.white },
  checkboxSelected: { backgroundColor: colors.forest, borderColor: colors.forest },
  searchRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  searchInput: { flex: 1 },
  searchButton: { width: 82, marginBottom: 16 },
  reload: { marginTop: 9 },
  bpRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.line, paddingVertical: 9 },
  empty: { marginTop: 12 },
  logout: { marginBottom: 24 },
});
