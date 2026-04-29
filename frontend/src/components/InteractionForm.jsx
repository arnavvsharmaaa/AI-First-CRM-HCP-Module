/**
 * InteractionForm.jsx
 *
 * LEFT panel of the Log Interaction screen (READ-ONLY form).
 *
 * Features added in Phase 5:
 *   1. Field highlight animation — any field whose key matches lastUpdatedField
 *      gets the CSS class `field-highlighted`, which animates from #e8f0fe → white
 *      over 1.5 s via a keyframe animation.  The class is removed after the
 *      animation ends so subsequent updates trigger it again.
 *
 *   2. Clickable AI Suggested Followup chips — clicking a chip appends its text
 *      to the Follow-up Actions field via Redux (updateFormFields).
 *
 *   3. Interaction Type rendered as a visual dropdown-style selector (read-only
 *      styled <select> that reflects the Redux value; actual AI sets it).
 */

import React, { useEffect, useRef, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { updateFormFields } from '../store/interactionSlice';
import './InteractionForm.css';

const INTERACTION_TYPES = ['Meeting', 'Call', 'Email', 'Conference'];

// ─── Hook: triggers highlight animation on a ref element ────────────────────
function useFieldHighlight(fieldName, lastUpdatedField) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    if (lastUpdatedField !== fieldName) return;

    const el = ref.current;
    // Remove and re-add class to re-trigger animation even if same field updated twice
    el.classList.remove('field-highlighted');
    // Force reflow so the browser registers the removal
    void el.offsetWidth;
    el.classList.add('field-highlighted');

    const onEnd = () => el.classList.remove('field-highlighted');
    el.addEventListener('animationend', onEnd, { once: true });
    return () => el.removeEventListener('animationend', onEnd);
  }, [fieldName, lastUpdatedField]);

  return ref;
}

// ─── Component ──────────────────────────────────────────────────────────────
const InteractionForm = () => {
  const interaction = useSelector((state) => state.interaction);
  const dispatch = useDispatch();
  const luf = interaction.lastUpdatedField; // shorthand

  // One ref per highlightable field
  const refHcpName         = useFieldHighlight('hcpName',           luf);
  const refInteractionType = useFieldHighlight('interactionType',    luf);
  const refDate            = useFieldHighlight('date',               luf);
  const refTime            = useFieldHighlight('time',               luf);
  const refAttendees       = useFieldHighlight('attendees',          luf);
  const refTopics          = useFieldHighlight('topicsDiscussed',    luf);
  const refMaterials       = useFieldHighlight('materialsShared',    luf);
  const refSamples         = useFieldHighlight('samplesDistributed', luf);
  const refSentiment       = useFieldHighlight('sentiment',          luf);
  const refOutcomes        = useFieldHighlight('outcomes',           luf);
  const refFollowUp        = useFieldHighlight('followUpActions',    luf);
  const refSuggestions     = useFieldHighlight('aiSuggestedFollowups', luf);

  // ── Chip click: append chip text to followUpActions ───────────────────────
  const handleChipClick = useCallback(
    (suggestion) => {
      const current = interaction.followUpActions;
      const separator = current && current.trim() ? '\n' : '';
      dispatch(
        updateFormFields({
          followUpActions: `${current}${separator}${suggestion}`,
          lastUpdatedField: 'followUpActions',
        })
      );
    },
    [interaction.followUpActions, dispatch]
  );

  // ── Helpers ───────────────────────────────────────────────────────────────
  const attendeesDisplay = Array.isArray(interaction.attendees)
    ? interaction.attendees.join(', ')
    : interaction.attendees;

  const materialsDisplay = Array.isArray(interaction.materialsShared)
    ? interaction.materialsShared.map((m) =>
        typeof m === 'object' ? `${m.name} (${m.type})` : m
      ).join('\n')
    : interaction.materialsShared;

  const samplesDisplay = Array.isArray(interaction.samplesDistributed)
    ? interaction.samplesDistributed.map((s) =>
        typeof s === 'object' ? `${s.product} x${s.quantity}` : s
      ).join('\n')
    : interaction.samplesDistributed;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="interaction-form-container">
      <h2 className="form-title">Log Interaction</h2>

      <div className="form-grid">

        {/* HCP Name */}
        <div className="form-group">
          <label htmlFor="field-hcp-name">HCP Name</label>
          <input
            id="field-hcp-name"
            ref={refHcpName}
            type="text"
            value={interaction.hcpName}
            readOnly
            placeholder="e.g. Dr. Jane Smith"
            className="read-only-input"
          />
        </div>

        {/* Interaction Type — working dropdown (AI-controlled) */}
        <div className="form-group">
          <label htmlFor="field-interaction-type">Interaction Type</label>
          <select
            id="field-interaction-type"
            ref={refInteractionType}
            value={interaction.interactionType}
            onChange={() => {}} // read-only — controlled by Redux only
            className="read-only-input read-only-select"
          >
            {INTERACTION_TYPES.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>

        {/* Date / Time */}
        <div className="form-row">
          <div className="form-group half">
            <label htmlFor="field-date">Date</label>
            <input
              id="field-date"
              ref={refDate}
              type="date"
              value={interaction.date}
              readOnly
              className="read-only-input"
            />
          </div>
          <div className="form-group half">
            <label htmlFor="field-time">Time</label>
            <input
              id="field-time"
              ref={refTime}
              type="time"
              value={interaction.time}
              readOnly
              className="read-only-input"
            />
          </div>
        </div>

        {/* Attendees */}
        <div className="form-group">
          <label htmlFor="field-attendees">Attendees</label>
          <input
            id="field-attendees"
            ref={refAttendees}
            type="text"
            value={attendeesDisplay}
            readOnly
            placeholder="Other attendees…"
            className="read-only-input"
          />
        </div>

        {/* Topics Discussed */}
        <div className="form-group">
          <label htmlFor="field-topics">Topics Discussed</label>
          <textarea
            id="field-topics"
            ref={refTopics}
            value={interaction.topicsDiscussed}
            readOnly
            placeholder="Details about the discussion…"
            className="read-only-input"
            rows={3}
          />
        </div>

        {/* Materials / Samples */}
        <div className="form-row">
          <div className="form-group half">
            <label htmlFor="field-materials">Materials Shared</label>
            <textarea
              id="field-materials"
              ref={refMaterials}
              value={materialsDisplay}
              readOnly
              className="read-only-input"
              rows={2}
            />
          </div>
          <div className="form-group half">
            <label htmlFor="field-samples">Samples Distributed</label>
            <textarea
              id="field-samples"
              ref={refSamples}
              value={samplesDisplay}
              readOnly
              className="read-only-input"
              rows={2}
            />
          </div>
        </div>

        {/* Sentiment */}
        <div className="form-group">
          <label>Sentiment</label>
          <div ref={refSentiment} className="sentiment-group">
            {['positive', 'neutral', 'negative'].map((val) => (
              <label key={val} className="sentiment-label">
                <input
                  type="radio"
                  checked={interaction.sentiment === val}
                  onChange={() => {}}
                  readOnly
                />
                <span className={`sentiment-radio ${val}`}>
                  {val.charAt(0).toUpperCase() + val.slice(1)}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Outcomes */}
        <div className="form-group">
          <label htmlFor="field-outcomes">Outcomes</label>
          <textarea
            id="field-outcomes"
            ref={refOutcomes}
            value={interaction.outcomes}
            readOnly
            placeholder="Key takeaways…"
            className="read-only-input"
            rows={2}
          />
        </div>

        {/* Follow-up Actions */}
        <div className="form-group">
          <label htmlFor="field-followup">Follow-up Actions</label>
          <textarea
            id="field-followup"
            ref={refFollowUp}
            value={interaction.followUpActions}
            readOnly
            placeholder="Next steps…"
            className="read-only-input"
            rows={2}
          />
        </div>

        {/* AI Suggested Follow-ups (clickable chips) */}
        <div className="form-group">
          <label>
            AI Suggested Follow-ups
            <span className="chip-hint"> — click a chip to add to Follow-up Actions</span>
          </label>
          <div ref={refSuggestions} className="ai-chips">
            {interaction.aiSuggestedFollowups.length > 0 ? (
              interaction.aiSuggestedFollowups.map((followup, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="ai-chip ai-chip-clickable"
                  onClick={() => handleChipClick(followup)}
                  title="Click to add to Follow-up Actions"
                >
                  {followup}
                </button>
              ))
            ) : (
              <span className="text-muted">No suggestions yet</span>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default InteractionForm;
