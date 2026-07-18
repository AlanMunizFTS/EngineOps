import { useState } from "react";

import type { ImplementationResponse, ImplementationStatus, MachineResponse } from "../api/client";

export interface MachineWithImplementations extends MachineResponse {
  implementations: ImplementationResponse[];
}

interface ProjectMachinesProps {
  machines: MachineWithImplementations[];
  onAddMachine: (name: string, machineType: string, location: string) => void;
  onAddImplementation: (
    machineId: string,
    label: string,
    status: ImplementationStatus,
  ) => void;
}

export default function ProjectMachines({
  machines,
  onAddMachine,
  onAddImplementation,
}: ProjectMachinesProps) {
  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-base font-semibold text-slate-900">Machines</h2>
      <NewMachineForm onSubmit={onAddMachine} />
      <div className="mt-4 space-y-4">
        {machines.map((machine) => (
          <MachineCard
            key={machine.id}
            machine={machine}
            onAddImplementation={onAddImplementation}
          />
        ))}
        {machines.length === 0 && (
          <p className="text-sm text-slate-500">No machines attached yet.</p>
        )}
      </div>
    </section>
  );
}

function NewMachineForm({
  onSubmit,
}: {
  onSubmit: (name: string, machineType: string, location: string) => void;
}) {
  const [name, setName] = useState("");
  const [machineType, setMachineType] = useState("");
  const [location, setLocation] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit(name, machineType, location);
    setName("");
    setMachineType("");
    setLocation("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
      <input
        type="text"
        placeholder="Machine name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="rounded border border-slate-300 px-2 py-1 text-sm"
      />
      <input
        type="text"
        placeholder="Type (optional)"
        value={machineType}
        onChange={(e) => setMachineType(e.target.value)}
        className="rounded border border-slate-300 px-2 py-1 text-sm"
      />
      <input
        type="text"
        placeholder="Location (optional)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        className="rounded border border-slate-300 px-2 py-1 text-sm"
      />
      <button
        type="submit"
        className="rounded bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-700"
      >
        Add machine
      </button>
    </form>
  );
}

function MachineCard({
  machine,
  onAddImplementation,
}: {
  machine: MachineWithImplementations;
  onAddImplementation: (
    machineId: string,
    label: string,
    status: ImplementationStatus,
  ) => void;
}) {
  const [label, setLabel] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!label.trim()) return;
    onAddImplementation(machine.id, label, "planned");
    setLabel("");
  }

  return (
    <div className="rounded border border-slate-200 p-4">
      <p className="font-medium text-slate-900">{machine.name}</p>
      <p className="text-xs text-slate-500">
        {[machine.machine_type, machine.location].filter(Boolean).join(" · ") || "No details"}
      </p>

      <ul className="mt-2 space-y-1">
        {machine.implementations.map((impl) => (
          <li key={impl.id} className="flex justify-between text-sm text-slate-700">
            <span>{impl.label}</span>
            <span className="text-slate-400">{impl.status}</span>
          </li>
        ))}
        {machine.implementations.length === 0 && (
          <li className="text-sm text-slate-400">No implementations yet.</li>
        )}
      </ul>

      <form onSubmit={handleSubmit} className="mt-2 flex gap-2">
        <input
          type="text"
          placeholder="New implementation label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm"
        />
        <button
          type="submit"
          className="rounded bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-700"
        >
          Add
        </button>
      </form>
    </div>
  );
}
