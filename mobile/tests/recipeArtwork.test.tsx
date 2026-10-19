import React from "react";
import { act, create } from "react-test-renderer";

import { RecipeArtwork } from "../src/components/RecipeArtwork";
import { useSession } from "../src/context/SessionContext";

jest.mock("../src/context/SessionContext", () => ({ useSession: jest.fn() }));

describe("RecipeArtwork", () => {
  it("uses the API path returned by the recipe instead of encoding it as an image ID", async () => {
    const text = jest.fn().mockRejectedValue(new Error("stop after checking the request"));
    (useSession as jest.Mock).mockReturnValue({ api: { text } });

    await act(async () => {
      create(<RecipeArtwork recipeId="/api/recipe-images/b1" />);
      await Promise.resolve();
    });

    expect(text).toHaveBeenCalledWith("/recipe-images/b1?lang=zh");
  });
});
