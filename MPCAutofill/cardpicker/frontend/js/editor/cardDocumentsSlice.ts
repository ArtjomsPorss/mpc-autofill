import {
  createSlice,
  createAsyncThunk,
  createSelector,
} from "@reduxjs/toolkit";
import Cookies from "js-cookie";

// import { AnyAction } from 'redux'
// import { RootState } from './store'
// import { ThunkAction } from 'redux-thunk'

// TODO: we should write something to read a page of card IDs from searchResults (100 at a time?) and query the backend for their full data
export const fetchCardDocuments = createAsyncThunk(
  "cardDocuments/fetchCardDocuments",
  async () => {
    const rawResponse = await fetch("/2/getCards/", {
      method: "POST",
      body: JSON.stringify({
        card_identifiers: [
          "1-BVOLIOK35eaNl2ytZtOlieejd0_D4z0",
          "1mCg4xFgdigH2Jyq8dmNHWOe1fht1Eoth",
          "1_rvQRbdskxqoRt94mh6JQrt9VgHdJY7h",
          "1YUOZcuGSJ5Kx4wuLR5bqhAkNUlnYq6fm",
          "1Ndv0ukuzfBA-eSar36EP2qJJuJuj5Ido",
          "1a3NSE99JqZw2ZQzmfatB4Im_TYDc700D",
          "1LrVX0pUcye9n_0RtaDNVl2xPrQgn7CYf",
          "1PxWVhIhUA_HAlHkCvx3O5O_HAaZhzyES",
        ],
      }),
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": Cookies.get("csrftoken"),
      },
    });
    const content = await rawResponse.json();
    return content.results;
  }
);

interface CardDocument {
  // This should match the data returned by `to_dict` on the `Card` Django model
  identifier: string;
  card_type: string;
  name: string;
  priority: number;
  source: string;
  source_verbose: string;
  source_type: string;
  dpi: number;
  searchq: string;
  extension: string;
  date: string; // formatted by backend
  download_link: string;
  size: number;
  small_thumbnail_url: string;
  medium_thumbnail_url: string;
}

interface CardDocuments {
  [key: string]: CardDocument;
}

interface CardDocumentsState {
  cardDocuments: CardDocuments;
  status: string;
  error: string;
}

const initialState: CardDocumentsState = {
  cardDocuments: {},
  status: "idle",
  error: null,
};

export const cardDocumentsSlice = createSlice({
  name: "cardDocuments",
  initialState,
  reducers: {
    addCardDocuments: (state, action) => {
      // state.results.push(...action.payload)
      state.cardDocuments = { ...state.cardDocuments, ...action.payload };
    },
  },
  extraReducers(builder) {
    // omit posts loading reducers
    builder.addCase(fetchCardDocuments.fulfilled, (state, action) => {
      // We can directly add the new post object to our posts array
      // state.posts.push(action.payload)
      state.cardDocuments = { ...state.cardDocuments, ...action.payload };
    });
  },
});
export const { addCardDocuments } = cardDocumentsSlice.actions;

// export const getCard = (state: any, cardIdentifier: string) => createSelector(state.cardDocuments.cardDocuments.get(cardIdentifier))

// const logAndAdd = (queries: Array<string>) => {
//   return (dispatch, getState) => {
//     const stateBefore = getState()
//     console.log(`Counter before: ${stateBefore.counter}`)
//     // dispatch(incrementByAmount(queries))
//     const stateAfter = getState()
//     console.log(`Counter after: ${stateAfter.counter}`)
//   }
// }

// export const addSearchResultsAsync = (queries: Array<[string, string]>) => (dispatch: any) => {
//   setTimeout(() => {
//     dispatch(addSearchResults(queries))
//   }, 1000)
// }

// Action creators are generated for each case reducer function
// export const { increment, decrement, incrementByAmount } = cardSlotSlice.actions

export default cardDocumentsSlice.reducer;
