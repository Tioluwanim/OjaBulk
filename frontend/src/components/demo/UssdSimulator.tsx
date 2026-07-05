"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Delete, PhoneCall, PhoneOff, RotateCcw } from "lucide-react";
import { sendUssdRequest } from "@/lib/api/ussd";
import { normalizeNigerianPhone } from "@/lib/phone";
import { Input } from "@/components/ui/Input";

const SERVICE_CODE = "*384#"; // update to match your registered Africa's Talking code

type SessionState = "idle" | "phone-entry" | "active" | "ended" | "error";

export function UssdSimulator() {
  const [state, setState] = useState<SessionState>("idle");
  const [phoneInput, setPhoneInput] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [accumulatedText, setAccumulatedText] = useState("");
  const [screenContent, setScreenContent] = useState("");
  const [currentInput, setCurrentInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const historyRef = useRef<string[]>([]);

  function startDialSetup() {
    setState("phone-entry");
    setError(null);
  }

  async function dial() {
    const normalized = normalizeNigerianPhone(phoneInput);
    if (!normalized) {
      setError("Enter a valid registered trader phone number.");
      return;
    }
    setError(null);
    setIsLoading(true);

    const newSessionId = crypto.randomUUID();
    setSessionId(newSessionId);
    setPhoneNumber(normalized);
    setAccumulatedText("");
    historyRef.current = [];

    try {
      const result = await sendUssdRequest({
        sessionId: newSessionId,
        serviceCode: SERVICE_CODE,
        phoneNumber: normalized,
        text: "",
      });
      setScreenContent(result.message);
      setState(result.mode === "END" ? "ended" : "active");
    } catch {
      setScreenContent("Could not reach the USSD gateway.");
      setState("error");
    } finally {
      setIsLoading(false);
    }
  }

  async function sendInput() {
    if (!currentInput) return;
    setIsLoading(true);
    setError(null);

    const nextText = accumulatedText
      ? `${accumulatedText}*${currentInput}`
      : currentInput;

    try {
      const result = await sendUssdRequest({
        sessionId,
        serviceCode: SERVICE_CODE,
        phoneNumber,
        text: nextText,
      });
      historyRef.current.push(screenContent);
      setAccumulatedText(nextText);
      setScreenContent(result.message);
      setCurrentInput("");
      setState(result.mode === "END" ? "ended" : "active");
    } catch {
      setError("Session error. Try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function hangUp() {
    setState("idle");
    setScreenContent("");
    setPhoneInput("");
    setPhoneNumber("");
    setAccumulatedText("");
    setCurrentInput("");
    setError(null);
  }

  const dialPad = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"];

  return (
    <div className="mx-auto w-full max-w-xs">
      {/* Phone frame */}
      <div className="rounded-[2.5rem] border-8 border-charcoal bg-charcoal p-3 shadow-2xl">
        {/* Screen */}
        <div className="relative flex h-[420px] flex-col rounded-2xl bg-[#c8d4b8] p-4 font-mono">
          {/* Signal bar */}
          <div className="mb-2 flex items-center justify-between text-[10px] text-charcoal/70">
            <span>OjaBulk USSD</span>
            <span>{SERVICE_CODE}</span>
          </div>

          <div className="flex-1 overflow-y-auto rounded-lg bg-[#b8c7a3] p-3 text-[13px] leading-relaxed text-charcoal">
            <AnimatePresence mode="wait">
              {state === "idle" && (
                <motion.p
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-charcoal/60"
                >
                  Dial {SERVICE_CODE} to check your OjaBulk balance and pool
                  status &mdash; no smartphone needed.
                </motion.p>
              )}

              {state === "phone-entry" && (
                <motion.div
                  key="phone-entry"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col gap-2"
                >
                  <p className="text-charcoal/70">
                    Enter a registered trader&apos;s phone number to simulate
                    the call:
                  </p>
                </motion.div>
              )}

              {(state === "active" || state === "ended" || state === "error") && (
                <motion.pre
                  key={screenContent}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="whitespace-pre-wrap font-mono text-[13px]"
                >
                  {screenContent}
                </motion.pre>
              )}
            </AnimatePresence>

            {isLoading && (
              <p className="mt-2 animate-pulse text-charcoal/50">
                Connecting to gateway...
              </p>
            )}
          </div>

          {/* Input row */}
          {state === "phone-entry" && (
            <div className="mt-3 flex flex-col gap-2">
              <Input
                type="tel"
                inputMode="tel"
                placeholder="0801 234 5678"
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                className="!py-2 !text-sm"
              />
              {error && <p className="text-xs text-danger">{error}</p>}
            </div>
          )}

          {state === "active" && (
            <div className="mt-3 rounded-lg bg-[#b8c7a3] px-3 py-2">
              <p className="min-h-[20px] font-mono text-sm text-charcoal">
                {currentInput || (
                  <span className="text-charcoal/40">Type your reply&hellip;</span>
                )}
              </p>
            </div>
          )}
        </div>

        {/* Dial pad / controls */}
        <div className="mt-3">
          {state === "idle" && (
            <button
              onClick={startDialSetup}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-success py-3 text-sm font-semibold text-white"
            >
              <PhoneCall className="h-4 w-4" />
              Dial {SERVICE_CODE}
            </button>
          )}

          {state === "phone-entry" && (
            <div className="flex gap-2">
              <button
                onClick={hangUp}
                className="flex flex-1 items-center justify-center gap-2 rounded-full bg-charcoal/60 py-3 text-sm font-semibold text-white"
              >
                Cancel
              </button>
              <button
                onClick={dial}
                disabled={isLoading}
                className="flex flex-1 items-center justify-center gap-2 rounded-full bg-success py-3 text-sm font-semibold text-white disabled:opacity-60"
              >
                <PhoneCall className="h-4 w-4" />
                Call
              </button>
            </div>
          )}

          {state === "active" && (
            <div className="flex flex-col gap-2">
              <div className="grid grid-cols-3 gap-2">
                {dialPad.map((key) => (
                  <button
                    key={key}
                    onClick={() => setCurrentInput((prev) => prev + key)}
                    className="rounded-xl bg-charcoal-soft py-2.5 text-center font-mono text-lg font-semibold text-cream transition-colors hover:bg-charcoal-soft/80"
                  >
                    {key}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentInput((prev) => prev.slice(0, -1))}
                  className="flex flex-1 items-center justify-center rounded-full bg-charcoal/60 py-2.5 text-cream"
                >
                  <Delete className="h-4 w-4" />
                </button>
                <button
                  onClick={sendInput}
                  disabled={isLoading || !currentInput}
                  className="flex flex-[2] items-center justify-center rounded-full bg-gold-500 py-2.5 text-sm font-semibold text-cream disabled:opacity-50"
                >
                  Send
                </button>
                <button
                  onClick={hangUp}
                  className="flex flex-1 items-center justify-center rounded-full bg-danger py-2.5 text-cream"
                >
                  <PhoneOff className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {(state === "ended" || state === "error") && (
            <button
              onClick={hangUp}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-gold-500 py-3 text-sm font-semibold text-cream"
            >
              <RotateCcw className="h-4 w-4" />
              Dial Again
            </button>
          )}
        </div>
      </div>

      <p className="mt-4 text-center text-xs text-charcoal-soft">
        This simulator sends real requests to your live{" "}
        <code className="rounded bg-cream-dark px-1.5 py-0.5">
          POST /ussd/session
        </code>{" "}
        endpoint &mdash; the same one Africa&apos;s Talking calls when a
        trader dials on an actual phone.
      </p>
    </div>
  );
}