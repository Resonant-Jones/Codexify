import { render, screen, fireEvent } from "@testing-library/react";
import IdentityMemorySettings from "../IdentityMemorySettings";
import * as api from "@/imprint/settingsApi";

describe("IdentityMemorySettings", () => {
  it("renders and saves changes", async () => {
    jest.spyOn(api, "fetchIdentitySettings").mockResolvedValue({
      memory_mode: "light",
      diary_requires_unlock: false,
      allow_sensitive_modeling: false,
    });
    const saveSpy = jest.spyOn(api, "saveIdentitySettings").mockResolvedValue({
      memory_mode: "none",
      diary_requires_unlock: true,
      allow_sensitive_modeling: true,
    });

    render(<IdentityMemorySettings />);

    const noneRadio = await screen.findByLabelText(/No identity memory/i);
    fireEvent.click(noneRadio);
    const diaryToggle = screen.getByLabelText(/Require unlock for diary threads/i);
    fireEvent.click(diaryToggle);
    const saveBtn = screen.getByText(/Save/i);
    fireEvent.click(saveBtn);

    expect(saveSpy).toHaveBeenCalled();
  });
});
