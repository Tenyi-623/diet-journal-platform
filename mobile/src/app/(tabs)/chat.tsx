import React, { useCallback, useEffect, useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { Button, LoadingBlock, Notice, PageHeading, Screen } from "../../components/UI";
import { useSession } from "../../context/SessionContext";
import { colors } from "../../theme";
import { t } from "../../i18n";
import type { ApiJob, ChatMessage, Recipe } from "../../types";
import { localized } from "../../types";

type ChatHistory = { messages: ChatMessage[]; active_job: ApiJob | null };
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function resultText(result: Record<string, unknown> | null | undefined, language: string) {
  if (typeof result?.message === "string") return result.message;
  if (result?.status === "ready") return language === "en" ? "A meal plan is ready. See the meals below." : language === "ja" ? "食事プランを作成しました。下のメニューをご確認ください。" : "已生成饮食方案，可查看下方餐次。";
  if (result?.status === "cancelled") return language === "en" ? "This request was cancelled." : language === "ja" ? "このリクエストはキャンセルされました。" : "本次请求已取消。";
  return language === "en" ? "No verified plan was generated. Please try again later." : language === "ja" ? "確認済みのプランを作成できませんでした。後でもう一度お試しください。" : "暂时没有生成可展示的方案，请稍后重试。";
}

export default function ChatScreen() {
  const { api, language } = useSession();
  const scrollRef = useRef<ScrollView>(null);
  const cancelledRef = useRef(false);
  const pendingRef = useRef<{ message: string; key: string } | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [activeJob, setActiveJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const finishJob = useCallback((job: ApiJob) => {
    const result = job.result ?? {};
    setMessages((current) => [
      ...current,
      { role: "assistant", content: resultText(result, language), data: result },
    ]);
    setActiveJob(null);
    setBusy(false);
  }, [language]);

  const pollJob = useCallback(async (jobId: string) => {
    cancelledRef.current = false;
    setActiveJob(jobId);
    setBusy(true);
    for (let attempt = 0; attempt < 120 && !cancelledRef.current; attempt += 1) {
      await wait(1500);
      if (cancelledRef.current) return;
      try {
        const job = await api.json<ApiJob>(`/recommendation-jobs/${jobId}`);
        if (job.status !== "queued" && job.status !== "running") {
          finishJob(job);
          return;
        }
      } catch (cause) {
        setBusy(false);
        setError(cause instanceof Error ? cause.message : "暂时无法读取回复状态。");
        return;
      }
    }
    if (!cancelledRef.current) {
      setBusy(false);
      setError("请求仍在处理中。你可以稍后重试查看，系统不会生成未验证的回复。");
    }
  }, [api, finishJob]);

  useEffect(() => {
    let mounted = true;
    cancelledRef.current = false;
    async function loadConversation() {
      try {
        const response = await api.json<{ sessions: { id: string }[] }>("/diet-chat/sessions");
        if (!mounted || !response.sessions.length) return;
        const latest = response.sessions[0];
        setSessionId(latest.id);
        const history = await api.json<ChatHistory>(`/diet-chat/sessions/${latest.id}`);
        if (!mounted) return;
        setMessages(history.messages ?? []);
        if (history.active_job?.job_id) void pollJob(history.active_job.job_id);
      } catch (cause) {
        if (mounted) setError(cause instanceof Error ? cause.message : "无法读取聊天记录。");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    void loadConversation();
    return () => {
      mounted = false;
      cancelledRef.current = true;
    };
  }, [api, pollJob]);

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    const pending = pendingRef.current?.message === text
      ? pendingRef.current
      : { message: text, key: `m${Date.now()}_${Math.random().toString(36).slice(2, 10)}` };
    pendingRef.current = pending;
    setError(null);
    try {
      const job = await api.json<ApiJob>("/diet-chat/messages", {
        method: "POST",
        body: JSON.stringify({
          message: pending.message,
          session_id: sessionId,
          language,
          idempotency_key: pending.key,
        }),
      });
      pendingRef.current = null;
      setDraft("");
      setSessionId(job.session_id ?? sessionId);
      setMessages((current) => [...current, { role: "user", content: pending.message }]);
      if (job.job_id) void pollJob(job.job_id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "消息未能发送，请重试。");
    }
  }

  async function cancel() {
    if (!activeJob) return;
    cancelledRef.current = true;
    try {
      const response = await api.json<{ result?: Record<string, unknown> }>(
        `/recommendation-jobs/${activeJob}/cancel`,
        { method: "POST", body: "{}" },
      );
      finishJob({ job_id: activeJob, status: "cancelled", result: response.result });
    } catch (cause) {
      setBusy(false);
      setError(cause instanceof Error ? cause.message : "无法取消当前请求。");
    }
  }

  function newConversation() {
    if (busy) return;
    pendingRef.current = null;
    setSessionId(null);
    setMessages([]);
    setDraft("");
    setError(null);
  }

  return (
    <Screen>
      <KeyboardAvoidingView style={styles.keyboard} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.top}>
          <PageHeading title={t(language, "chat")} subtitle={t(language, "chatSubtitle")} />
          <Pressable accessibilityRole="button" onPress={newConversation} disabled={busy} style={styles.newButton}>
            <Text style={styles.newButtonText}>{t(language, "newChat")}</Text>
          </Pressable>
        </View>
        {error ? <Notice message={error} error /> : null}
        {loading ? <LoadingBlock label="正在读取聊天记录…" /> : (
          <ScrollView
            ref={scrollRef}
            style={styles.messages}
            contentContainerStyle={styles.messageList}
            keyboardShouldPersistTaps="handled"
            onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          >
            {messages.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyMark}>✦</Text>
                <Text style={styles.emptyTitle}>{t(language, "emptyChatTitle")}</Text>
                <Text style={styles.emptySubtitle}>{t(language, "emptyChatPrompt")}</Text>
              </View>
            ) : null}
            {messages.map((message, index) => (
              <View key={`${index}-${message.role}`} style={[styles.messageRow, message.role === "user" && styles.userRow]}>
                {message.role === "assistant" ? <View style={styles.assistantMark}><Text style={styles.assistantLeaf}>✦</Text></View> : null}
                <View style={[styles.bubble, message.role === "user" ? styles.userBubble : styles.assistantBubble]}>
                  <Text style={styles.messageText}>{message.content}</Text>
                  {Array.isArray(message.data?.meals) ? (
                    <View style={styles.meals}>
                      {(message.data.meals as Recipe[]).map((meal) => (
                        <Text key={`${meal.recipe_id}-${meal.meal}`} style={styles.mealLink}>
                          {t(language, meal.meal === "breakfast" ? "mealBreakfast" : meal.meal === "lunch" ? "mealLunch" : "mealDinner")} · {localized(meal.name, language)}
                        </Text>
                      ))}
                    </View>
                  ) : null}
                </View>
              </View>
            ))}
            {busy ? (
              <View style={styles.processing}><LoadingBlock label={t(language, "processing")} /><Button title={t(language, "cancel")} secondary onPress={() => void cancel()} /></View>
            ) : null}
          </ScrollView>
        )}
        <View style={styles.composer}>
          <TextInput
            accessibilityLabel="饮食问题"
            multiline
            maxLength={1500}
            placeholder={t(language, "chatInput")}
            placeholderTextColor={colors.muted}
            value={draft}
            onChangeText={setDraft}
            editable={!busy}
            style={styles.input}
          />
          <Pressable accessibilityRole="button" accessibilityLabel="发送" disabled={!draft.trim() || busy} onPress={() => void send()} style={[styles.send, (!draft.trim() || busy) && styles.sendDisabled]}>
            <Text style={styles.sendText}>↑</Text>
          </Pressable>
        </View>
        <Text style={styles.disclaimer}>{t(language, "chatDisclaimer")}</Text>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  keyboard: { flex: 1 },
  top: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  newButton: { marginTop: 25, backgroundColor: colors.leaf, borderRadius: 99, paddingHorizontal: 12, paddingVertical: 8 },
  newButtonText: { color: colors.forest, fontSize: 13, fontWeight: "700" },
  messages: { flex: 1, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, borderRadius: 18 },
  messageList: { padding: 14, gap: 14, flexGrow: 1, justifyContent: "flex-end" },
  empty: { flex: 1, minHeight: 240, alignItems: "center", justifyContent: "center", gap: 9 },
  emptyMark: { color: colors.forest, fontSize: 28 },
  emptyTitle: { color: colors.ink, fontSize: 20, fontWeight: "700" },
  emptySubtitle: { color: colors.muted, fontSize: 13, textAlign: "center" },
  messageRow: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  userRow: { justifyContent: "flex-end" },
  assistantMark: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.leaf, alignItems: "center", justifyContent: "center" },
  assistantLeaf: { color: colors.forest, fontSize: 15 },
  bubble: { maxWidth: "83%", paddingHorizontal: 14, paddingVertical: 11, borderRadius: 16 },
  userBubble: { backgroundColor: colors.leaf, borderBottomRightRadius: 5 },
  assistantBubble: { backgroundColor: "#F8F9F6", borderWidth: 1, borderColor: colors.line, borderBottomLeftRadius: 5 },
  messageText: { color: colors.ink, fontSize: 14, lineHeight: 21 },
  meals: { borderTopColor: colors.line, borderTopWidth: 1, marginTop: 10, paddingTop: 8, gap: 5 },
  mealLink: { color: colors.forest, fontSize: 13, fontWeight: "600" },
  processing: { gap: 5, alignItems: "stretch", paddingTop: 10 },
  composer: { flexDirection: "row", alignItems: "flex-end", backgroundColor: colors.white, borderColor: colors.line, borderWidth: 1, borderRadius: 15, padding: 8, marginTop: 12 },
  input: { flex: 1, maxHeight: 110, minHeight: 42, color: colors.ink, fontSize: 15, paddingHorizontal: 9, paddingTop: 10, paddingBottom: 8 },
  send: { width: 42, height: 42, borderRadius: 12, backgroundColor: colors.forest, alignItems: "center", justifyContent: "center" },
  sendDisabled: { backgroundColor: "#D6DAD6" },
  sendText: { color: colors.white, fontSize: 23, lineHeight: 25, fontWeight: "700" },
  disclaimer: { color: colors.muted, fontSize: 10, textAlign: "center", marginVertical: 8 },
});
