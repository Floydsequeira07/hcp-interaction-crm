import { createSlice } from "@reduxjs/toolkit";

const initialState = {
    doctorName: "",
    interactionType: "",
    date: "",
    time: "",
    attendees: "",
    topics: "",
    materialsShared: [],
    samplesDistributed: [],
    sentiment: "",
    outcome: "",
    followUp: "",
    summary: "",
    messages: []
}

const interactionSlice = createSlice({
    name: "interaction",
    initialState,
    reducers: {
        updateField: (state, action) => {
            state[action.payload.field] = action.payload.value
        },

        setInteraction: (state, action) => {
            return {
                ...state,
                ...action.payload
            }
        },

        addMessage: (state, action) => {
            state.messages.push(action.payload)
        },

        clearInteraction: () => initialState,

        // Resets only the form fields, preserving chat message history.
        // Use this for automatic clears triggered by chat responses (e.g.
        // "no interaction history found") so the conversation isn't wiped
        // out as a side effect. clearInteraction (full reset, including
        // messages) stays reserved for explicit user actions like the
        // "Clear Draft" button.
        clearFormFields: (state) => {
            const { messages, ...formInitialState } = initialState;
            return {
                ...formInitialState,
                messages: state.messages
            }
        }
    }
})

export const {
    updateField,
    setInteraction,
    addMessage,
    clearInteraction,
    clearFormFields
} = interactionSlice.actions

export default interactionSlice.reducer