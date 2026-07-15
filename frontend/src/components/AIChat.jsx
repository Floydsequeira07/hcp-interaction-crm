import { useState } from "react";
import { Bot, Sparkles, Send } from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import {
  addMessage,
  updateField,
  clearFormFields,
} from "../features/interaction/interactionSlice";

const toArray = (val) => {
  if (Array.isArray(val)) return val;
  if (typeof val === "string" && val.trim()) {
    return val.split(",").map((s) => s.trim()).filter(Boolean);
  }
  return [];
};

const toTitleCase = (val) => {
  if (!val || typeof val !== "string") return "";
  return val.charAt(0).toUpperCase() + val.slice(1).toLowerCase();
};

// Maps backend response keys -> Redux field name + how to transform the value.
// Only fields that are ACTUALLY present in the response get dispatched, so a
// partial edit response like {"hcp_name": "Dr. Priya"} only touches doctorName
// and leaves every other field exactly as it was.
const FIELD_HANDLERS = {
  hcp_name: (v) => ({ field: "doctorName", value: v }),
  interaction_type: (v) => ({ field: "interactionType", value: toTitleCase(v) }),
  date: (v) => ({ field: "date", value: v }),
  time: (v) => ({ field: "time", value: v }),
  attendees: (v) => ({ field: "attendees", value: v }),
  topics_discussed: (v) => ({ field: "topics", value: v }),
  materials_shared: (v) => ({ field: "materialsShared", value: toArray(v) }),
  samples_distributed: (v) => ({ field: "samplesDistributed", value: toArray(v) }),
  sentiment: (v) => ({ field: "sentiment", value: toTitleCase(v) }),
  outcomes: (v) => ({ field: "outcome", value: v }),
  follow_up_actions: (v) => ({ field: "followUp", value: v }),
};

const applyFieldHandlers = (dispatch, obj) => {
  for (const [key, handler] of Object.entries(FIELD_HANDLERS)) {
    if (Object.prototype.hasOwnProperty.call(obj, key) && obj[key] !== null) {
      dispatch(updateField(handler(obj[key])));
    }
  }
};

export default function AIChat() {
  const dispatch = useDispatch();
  const messages = useSelector((state) => state.interaction.messages);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    console.log("1. sendMessage called");

    if (!input.trim()) return;

    dispatch(addMessage({ role: "user", content: input }));

    const message = input;
    setInput("");

    try {
      console.log("2. Before fetch");

      const res = await fetch(`${import.meta.env.VITE_API_URL}/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      console.log("3. Status:", res.status);

      const text = await res.text();
      console.log("4. Response:", text);

      const data = JSON.parse(text);

      // get_hcp_history responses look like {"hcp_name": ..., "interactions": [...]}.
      // - No interactions found -> clear the draft form entirely.
      // - Interactions found -> populate the form with the most recent one
      //   (interactions[0], since the backend orders by id desc), same as a
      //   log/edit response would, so the form mirrors what's shown in chat.
      const isHistoryResponse = Object.prototype.hasOwnProperty.call(data, "interactions");

      if (isHistoryResponse) {
        if (Array.isArray(data.interactions) && data.interactions.length > 0) {
          const latest = data.interactions[0];
          applyFieldHandlers(dispatch, {
            hcp_name: data.hcp_name,
            ...latest,
          });
        } else {
          dispatch(clearFormFields());
        }
      } else {
        // Only dispatch fields that are actually present in this response —
        // NEVER fall back to "" for a missing key, since that's what was
        // wiping out untouched fields on partial edit responses.
        applyFieldHandlers(dispatch, data);
      }

      dispatch(
        addMessage({
          role: "success",
          content: data.ai_response,
        })
      );
    } catch (err) {
      console.error("Fetch Error:", err);

      dispatch(
        addMessage({
          role: "error",
          content: err.message,
        })
      );
    }
  };

  return (
    <div className="aichat-wrapper">
      {/* Header */}
      <div className="aichat-header">
        <div className="aichat-header-row">
          <div className="aichat-icon-badge">
            <Bot size={18} color="#4f46e5" />
          </div>
          <h2 className="aichat-title">AI Assistant</h2>
        </div>
        <p className="aichat-subtitle">Log Interaction details here via chat</p>
      </div>

      {/* Messages */}
      <div className="aichat-messages">
        <div className="aichat-hint-box">
          Log interaction details here (e.g., "Met Dr. Smith, discussed
          Prodo-X efficacy, positive sentiment, shared brochure") or ask
          for help.
        </div>

        {messages.map((m, i) => {
          if (m.role === "user") {
            return (
              <div key={i} className="aichat-row-end">
                <div className="aichat-bubble-user">{m.content}</div>
              </div>
            );
          }
          if (m.role === "success") {
            return (
              <div key={i} className="aichat-row-start">
                <div className="aichat-bubble-success">
                  <span style={{ whiteSpace: "pre-line" }}>{m.content}</span>
                </div>
              </div>
            );
          }
          return (
            <div key={i} className="aichat-row-start">
              <div className="aichat-bubble-default">{m.content}</div>
            </div>
          );
        })}
      </div>

      {/* Input */}
      <div className="aichat-input-area">
        <div className="aichat-try-row">
          <Sparkles size={13} />
          <span>
            Try: "Visited Dr. Sharma today, discussed Product X, positive
            feedback"
          </span>
        </div>

        <div className="aichat-input-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Describe Interaction..."
            className="aichat-text-input"
          />
          <button
            onClick={sendMessage}
            className="aichat-send-button"
            aria-label="Send"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}