/**
 * Trackside Coach Dashboard — Notes & Track Zones Hook.
 * Handles zone selection, new zone creation, and coach observation notes.
 */

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";
import { SessionNote, TrackZone, DriverProfile } from "../types";
import { DEFAULT_SPRINT_FLOOR, DEFAULT_SPRINT_CEILING } from "../constants";

export function useCoachNotes(
  activeSessionId: string | null,
  activeTrackId: string | null,
  selectedDriver: DriverProfile,
) {
  const [zones, setZones] = useState<TrackZone[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>("");
  const [isCreatingZone, setIsCreatingZone] = useState<boolean>(false);
  const [newZoneName, setNewZoneName] = useState<string>("");
  const [newCornerType, setNewCornerType] = useState<string>("hairpin");
  const [isSavingZone, setIsSavingZone] = useState<boolean>(false);

  const [notes, setNotes] = useState<SessionNote[]>([]);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [newNoteText, setNewNoteText] = useState("");

  // Load the zones of the active session's own track (empty when there is no track)
  useEffect(() => {
    setZones([]);
    setSelectedZoneId("");
    if (!activeTrackId) return;
    let cancelled = false;
    async function loadZones() {
      try {
        const zonesRes = await api.get<any>(`/api/tracks/${activeTrackId}/zones/`);
        const zoneList = Array.isArray(zonesRes) ? zonesRes : zonesRes.results || [];
        if (cancelled || zoneList.length === 0) return;
        const mappedZones: TrackZone[] = zoneList.map((z: any) => ({
          id: z.id,
          label: z.label || z.name || `Zone ${z.order_number || z.id}`,
          corner_type: z.corner_type || "other",
          threshold_g: typeof z.threshold_g === "number" ? z.threshold_g : DEFAULT_SPRINT_CEILING,
          min_threshold_g: typeof z.min_threshold_g === "number" ? z.min_threshold_g : DEFAULT_SPRINT_FLOOR,
        }));
        setZones(mappedZones);
        setSelectedZoneId(mappedZones[0].id);
      } catch (err) {
        console.warn("Could not load the zones of the active track:", err);
      }
    }
    loadZones();
    return () => {
      cancelled = true;
    };
  }, [activeTrackId]);

  // Fetch Notes for Active Session from API
  useEffect(() => {
    setNotes([]);
    if (!activeSessionId) return;
    let cancelled = false;
    async function loadNotes() {
      try {
        const res = await api.get<any>(`/api/sessions/${activeSessionId}/notes/`);
        if (cancelled) return;
        const noteList = Array.isArray(res) ? res : res.results || [];
        const mapped: SessionNote[] = noteList.map((n: any) => ({
          id: n.id,
          timestamp: n.created_at
            ? new Date(n.created_at).toLocaleTimeString("en-GB")
            : new Date().toLocaleTimeString("en-GB"),
          driverName: n.coach_name || selectedDriver.name,
          kart: selectedDriver.kart,
          zone: n.zone_label || "General",
          lap: "Lap 5",
          text: n.note_text || n.text || "",
        }));
        setNotes(mapped);
      } catch (err) {
        console.error("Failed loading session notes:", err);
      }
    }
    loadNotes();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, selectedDriver.name, selectedDriver.id]);

  const handleZoneSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "__new__") {
      setIsCreatingZone(true);
      setSelectedZoneId("__new__");
    } else {
      setIsCreatingZone(false);
      setSelectedZoneId(val);
    }
  };

  const handleCreateZone = async () => {
    if (!newZoneName.trim()) return null;
    const name = newZoneName.trim();
    setIsSavingZone(true);
    try {
      const targetTrackId = activeTrackId;
      if (targetTrackId) {
        const res: any = await api.post(`/api/tracks/${targetTrackId}/zones/`, {
          label: name,
          corner_type: newCornerType,
        });

        if (res && res.id) {
          const createdZone: TrackZone = {
            id: res.id,
            label: res.label || name,
            corner_type: res.corner_type || newCornerType,
          };
          setZones((prev) => [...prev, createdZone]);
          setSelectedZoneId(createdZone.id);
          setIsCreatingZone(false);
          setNewZoneName("");
          return createdZone;
        }
      }
    } catch (err) {
      console.error("Failed creating zone via API:", err);
    } finally {
      setIsSavingZone(false);
    }
    return null;
  };

  const handleAddNote = async () => {
    setNoteError(null);
    if (!newNoteText.trim()) return;

    let currentZoneId = selectedZoneId;
    if (currentZoneId === "__new__") {
      const created = await handleCreateZone();
      if (created) {
        currentZoneId = created.id;
      } else {
        setNoteError("Could not add that corner here. Add corners in Maps & Demo > Edit corners, then pick it for the note.");
        return;
      }
    }

    const selectedZoneObj = zones.find((z) => z.id === currentZoneId);
    const noteText = newNoteText.trim();

    if (!activeSessionId) {
      setNoteError("No active driving session available to record notes.");
      return;
    }

    try {
      const payload: any = { note_text: noteText };
      if (selectedZoneObj && selectedZoneObj.id) {
        payload.zone = selectedZoneObj.id;
      }
      const res = await api.post<any>(`/api/sessions/${activeSessionId}/notes/`, payload);
      const createdNote: SessionNote = {
        id: res.id,
        timestamp: res.created_at
          ? new Date(res.created_at).toLocaleTimeString("en-GB")
          : new Date().toLocaleTimeString("en-GB"),
        driverName: res.coach_name || selectedDriver.name,
        zone: res.zone_label || (selectedZoneObj ? selectedZoneObj.label : "General"),
        lap: "Lap 7",
        text: noteText,
      };
      setNotes((prev) => [createdNote, ...prev]);
      setNewNoteText("");
    } catch (err: any) {
      setNoteError(err.message || "Failed to save note to server.");
    }
  };

  return {
    zones,
    selectedZoneId,
    setSelectedZoneId,
    isCreatingZone,
    setIsCreatingZone,
    newZoneName,
    setNewZoneName,
    newCornerType,
    setNewCornerType,
    isSavingZone,
    handleZoneSelectChange,
    handleCreateZone,
    notes,
    noteError,
    newNoteText,
    setNewNoteText,
    handleAddNote,
  };
}
