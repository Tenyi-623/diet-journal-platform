import { bloodPressureRecordFromCreate } from "../src/lib/bloodPressure";

describe("bloodPressureRecordFromCreate", () => {
  it("combines the backend's id/note acknowledgement with the submitted measurement", () => {
    expect(
      bloodPressureRecordFromCreate(
        { id: 42, note: "仅记录，不根据单次测量诊断或修改治疗。" },
        {
          systolic: 128,
          diastolic: 82,
          measured_at: "2026-10-13T02:15:00.000Z",
        },
      ),
    ).toEqual({
      id: 42,
      systolic: 128,
      diastolic: 82,
      measured_at: "2026-10-13T02:15:00.000Z",
    });
  });
});
