import { describe, expect, it } from "vitest";
import { messageFromErrorBody } from "../api-errors";

describe("messageFromErrorBody", () => {
  it("uses detail when the server sends one", () => {
    expect(messageFromErrorBody({ detail: "Too many failed sign-in attempts." }, "fallback")).toBe(
      "Too many failed sign-in attempts.",
    );
  });

  it("turns field errors into readable sentences", () => {
    const body = { password: ["This password is too common.", "This password is entirely numeric."] };
    expect(messageFromErrorBody(body, "fallback")).toBe(
      "Password: This password is too common. Password: This password is entirely numeric.",
    );
  });

  it("drops the label for non-field errors and reads nested errors", () => {
    expect(messageFromErrorBody({ non_field_errors: ["Choose an active driver."] }, "x")).toBe("Choose an active driver.");
    expect(messageFromErrorBody({ payload: { peak_g: "is required" } }, "x")).toBe("payload: is required");
  });

  it("falls back when the body is empty or not an object", () => {
    expect(messageFromErrorBody({}, "Request failed with status 500")).toBe("Request failed with status 500");
    expect(messageFromErrorBody(null, "fallback")).toBe("fallback");
  });
});
