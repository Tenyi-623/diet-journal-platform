export type BloodPressureMeasurement = {
  systolic: number;
  diastolic: number;
  measured_at: string;
};

export type BPRecord = BloodPressureMeasurement & { id: number };

export type CreateBloodPressureResponse = {
  id: number;
  note: string;
};

export function bloodPressureRecordFromCreate(
  response: CreateBloodPressureResponse,
  measurement: BloodPressureMeasurement,
): BPRecord {
  return { id: response.id, ...measurement };
}
