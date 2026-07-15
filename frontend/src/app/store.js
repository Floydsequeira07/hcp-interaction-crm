import { configureStore } from "@reduxjs/toolkit";

import interactionReducer from "../features/interaction/interactionSlice";

export const store = configureStore({

    reducer:{

        interaction:interactionReducer

    }

})