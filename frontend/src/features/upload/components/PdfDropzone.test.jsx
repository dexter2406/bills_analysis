import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PdfDropzone } from "./PdfDropzone";

describe("PdfDropzone", () => {
  it("passes selected files to callback", () => {
    const onFilesAdded = vi.fn();
    render(<PdfDropzone onFilesAdded={onFilesAdded} />);

    const input = document.querySelector('input[type="file"]');
    const file = new File(["pdf"], "bill.pdf", { type: "application/pdf" });

    fireEvent.change(input, {
      target: { files: [file] },
    });

    expect(onFilesAdded).toHaveBeenCalledTimes(1);
  });

  it("renders upload hint", () => {
    render(<PdfDropzone onFilesAdded={() => {}} />);
    expect(screen.getByText(/Only \.pdf files are accepted/i)).toBeInTheDocument();
  });
});
