import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { updateField, clearInteraction } from "../features/interaction/interactionSlice";
import { saveInteraction } from "../services/interactionApi";
import toast from "react-hot-toast";
import {
  User, Calendar, Clock3, Users, NotebookPen, Eraser,
  Smile, Meh, Frown, Search, Plus, Save,
} from "lucide-react";

// Defined OUTSIDE HCPForm so it keeps a stable identity across renders.
// (Previously this was declared inside HCPForm, so React recreated it on
// every keystroke and unmounted/remounted the <input>, causing focus loss
// after a single character.)
function Field({ icon, label, name, type = "text", placeholder = "", value, onChange }) {
  return (
    <div className="hcpform-field">
      <label className="hcpform-label">
        {icon} {label}
      </label>
      <input
        type={type}
        name={name}
        value={value ?? ""}
        onChange={onChange}
        placeholder={placeholder}
        className="hcpform-input"
      />
    </div>
  );
}

export default function HCPForm() {
  const dispatch = useDispatch();
  const form = useSelector((state) => state.interaction);

  const prevForm = useRef(form);
  const [flashed, setFlashed] = useState({});

  useEffect(() => {
    const changed = {};
    Object.keys(form).forEach((key) => {
      if (key === "messages") return;
      if (JSON.stringify(prevForm.current[key]) !== JSON.stringify(form[key])) {
        changed[key] = true;
      }
    });
    if (Object.keys(changed).length) {
      setFlashed(changed);
      const t = setTimeout(() => setFlashed({}), 1200);
      prevForm.current = form;
      return () => clearTimeout(t);
    }
    prevForm.current = form;
  }, [form]);

  const handleChange = (e) => {
    dispatch(updateField({ field: e.target.name, value: e.target.value }));
  };

  const addMaterial = () => {
    const value = window.prompt("Material name (e.g. Prodo-X Efficacy Brochure)");
    if (value?.trim()) {
      dispatch(updateField({
        field: "materialsShared",
        value: [...(form.materialsShared || []), value.trim()],
      }));
    }
  };

  const addSample = () => {
    const value = window.prompt("Sample name (e.g. Prodo-X 10mg Sample Pack)");
    if (value?.trim()) {
      dispatch(updateField({
        field: "samplesDistributed",
        value: [...(form.samplesDistributed || []), value.trim()],
      }));
    }
  };

  const handleSave = async () => {
  try {
    const payload = {
      hcp_name: form.doctorName || "",
      interaction_type: form.interactionType || "",
      date: form.date,
      time: form.time,
      attendees: form.attendees || "",
      topics_discussed: form.topics || "",
      materials_shared: (form.materialsShared || []).join(", "),
      samples_distributed: (form.samplesDistributed || []).join(", "),
      sentiment: form.sentiment || "",
      outcomes: form.outcome || "",
      follow_up_actions: form.followUp || "",
    };

    console.log("Payload:", payload);

    await saveInteraction(payload);

    toast.success("Interaction saved successfully!");

    dispatch(clearInteraction());

  } catch (error) {

    console.error("API Error:", error.response?.data);

    toast.error("Failed to save interaction.");
  }
};
  return (
    <div className="hcpform-wrapper">
      <h2 className="hcpform-title">Log HCP Interaction</h2>

      <h3 className="hcpform-section-label">Interaction Details</h3>

      <div className="hcpform-grid">
        <Field
          icon={<User size={16} />}
          label="HCP Name"
          name="doctorName"
          placeholder="Search or select HCP..."
          value={form.doctorName}
          onChange={handleChange}
        />

        <div className="hcpform-field">
          <label className="hcpform-label">Interaction Type</label>
          <select
            name="interactionType"
            value={form.interactionType ?? ""}
            onChange={handleChange}
            className="hcpform-select"
          >
            <option value="">Select</option>
            <option>Visit</option>
            <option>Call</option>
            <option>Meeting</option>
            <option>Conference</option>
          </select>
        </div>

        <Field
          icon={<Calendar size={16} />}
          label="Date"
          name="date"
          type="date"
          value={form.date}
          onChange={handleChange}
        />
        <Field
          icon={<Clock3 size={16} />}
          label="Time"
          name="time"
          type="time"
          value={form.time}
          onChange={handleChange}
        />
      </div>

      <div className="hcpform-block">
        <Field
          icon={<Users size={16} />}
          label="Attendees"
          name="attendees"
          placeholder="Enter names or search..."
          value={form.attendees}
          onChange={handleChange}
        />
      </div>

      <div className="hcpform-block">
        <label className="hcpform-label">
          <NotebookPen size={16} /> Topics Discussed
        </label>
        <textarea
          rows="4"
          name="topics"
          value={form.topics ?? ""}
          onChange={handleChange}
          className="hcpform-textarea"
          placeholder="Enter key discussion points..."
        />
      </div>

      {/* Materials Shared / Samples Distributed */}
      <div className="hcpform-block">
        <h3 className="hcpform-section-label">Materials Shared / Samples Distributed</h3>

        <div className="hcpform-materials-card">
          <div className="hcpform-materials-header">
            <label className="hcpform-materials-title">Materials Shared</label>
            <button onClick={addMaterial} type="button" className="hcpform-add-btn">
              <Search size={14} /> Search/Add
            </button>
          </div>
          {(form.materialsShared || []).length === 0 ? (
            <p className="hcpform-empty-note">No materials added.</p>
          ) : (
            <div className="hcpform-chip-row">
              {form.materialsShared.map((m, i) => (
                <span key={i} className="hcpform-chip-blue">{m}</span>
              ))}
            </div>
          )}
        </div>

        <div className="hcpform-materials-card">
          <div className="hcpform-materials-header">
            <label className="hcpform-materials-title">Samples Distributed</label>
            <button onClick={addSample} type="button" className="hcpform-add-btn">
              <Plus size={14} /> Add Sample
            </button>
          </div>
          {(form.samplesDistributed || []).length === 0 ? (
            <p className="hcpform-empty-note">No samples added.</p>
          ) : (
            <div className="hcpform-chip-row">
              {form.samplesDistributed.map((s, i) => (
                <span key={i} className="hcpform-chip-green">{s}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sentiment */}
      <div className="hcpform-block">
        <label className="hcpform-section-label">Observed/Inferred HCP Sentiment</label>
        <div className="hcpform-sentiment-row">
          {[
            { value: "Positive", icon: <Smile size={16} className="text-green-600" /> },
            { value: "Neutral", icon: <Meh size={16} className="text-amber-500" /> },
            { value: "Negative", icon: <Frown size={16} className="text-red-500" /> },
          ].map(({ value, icon }) => (
            <label key={value} className="hcpform-sentiment-option">
              <input
                type="radio"
                name="sentiment"
                value={value}
                checked={form.sentiment === value}
                onChange={handleChange}
              />
              {icon} {value}
            </label>
          ))}
        </div>
      </div>

      <div className="hcpform-block">
        <label className="hcpform-label">Outcomes</label>
        <textarea
          rows="3"
          name="outcome"
          value={form.outcome ?? ""}
          onChange={handleChange}
          className="hcpform-textarea"
          placeholder="Key outcomes or agreements..."
        />
      </div>

      <div className="hcpform-block">
        <label className="hcpform-label">Follow-up Actions</label>
        <textarea
          rows="2"
          name="followUp"
          value={form.followUp ?? ""}
          onChange={handleChange}
          className="hcpform-textarea"
          placeholder="Next action..."
        />
      </div>

      <div className="hcpform-footer">
        <button className="hcpform-save-btn" type="button" onClick={handleSave}>
          <Save size={18} /> Save Interaction
        </button>
        <button
          onClick={() => dispatch(clearInteraction())}
          className="hcpform-clear-btn"
          type="button"
        >
          <Eraser size={18} /> Clear Draft
        </button>
      </div>
    </div>
  );
}