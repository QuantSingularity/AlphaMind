import { researchService } from "../../services/researchService";

jest.mock("../../services/api", () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  },
}));

jest.mock("../../constants/config", () => ({
  API_ENDPOINTS: {
    RESEARCH: {
      PAPERS: "/api/research/papers",
      DETAILS: (id) => `/api/research/papers/${id}`,
    },
  },
  ENABLE_MOCK_DATA: false,
}));

import api from "../../services/api";

const mockPapers = [
  {
    id: "1",
    title: "Deep Learning for Market Prediction",
    summary: "Test summary",
    authors: ["Dr. John Smith"],
    date: "2025-11-15",
    category: "Machine Learning",
    url: "https://example.com/paper1.pdf",
  },
];

describe("researchService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("getPapers", () => {
    it("fetches papers from API", async () => {
      api.get.mockResolvedValueOnce({ data: mockPapers });

      const result = await researchService.getPapers();
      expect(api.get).toHaveBeenCalledWith("/api/research/papers", {
        params: {},
      });
      expect(result).toEqual(mockPapers);
    });

    it("passes filters as params", async () => {
      api.get.mockResolvedValueOnce({ data: [] });

      await researchService.getPapers({ category: "Machine Learning" });
      expect(api.get).toHaveBeenCalledWith("/api/research/papers", {
        params: { category: "Machine Learning" },
      });
    });

    it("propagates API errors", async () => {
      api.get.mockRejectedValueOnce({ message: "Not found" });
      await expect(researchService.getPapers()).rejects.toEqual({
        message: "Not found",
      });
    });
  });

  describe("getPaperDetails", () => {
    it("fetches paper by id", async () => {
      api.get.mockResolvedValueOnce({ data: mockPapers[0] });

      const result = await researchService.getPaperDetails("1");
      expect(api.get).toHaveBeenCalledWith("/api/research/papers/1");
      expect(result).toEqual(mockPapers[0]);
    });

    it("propagates error when paper not found", async () => {
      api.get.mockRejectedValueOnce({ message: "Not found", status: 404 });
      await expect(
        researchService.getPaperDetails("999"),
      ).rejects.toMatchObject({
        message: "Not found",
      });
    });
  });
});
