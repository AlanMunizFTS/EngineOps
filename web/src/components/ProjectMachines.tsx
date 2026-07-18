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

const STATUS_STYLES: Record<ImplementationStatus, string> = {
  planned: "bg-ink-700 text-slate-300",
  active: "bg-ember-500/15 text-ember-400",
  superseded: "bg-amber-500/15 text-amber-400",
  decommissioned: "bg-slate-600/20 text-slate-500",
};

export default function ProjectMachines({
  machines,
  onAddMachine,
  onAddImplementation,
}: ProjectMachinesProps) {
  return (
    <section className="rounded-2xl border border-ink-800 bg-ink-900 p-6 shadow-lg shadow-black/20">
      <h2 className="mb-4 text-base font-semibold text-slate-100">Machines</h2>
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
        className="rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <input
        type="text"
        placeholder="Type (optional)"
        value={machineType}
        onChange={(e) => setMachineType(e.target.value)}
        className="rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <input
        type="text"
        placeholder="Location (optional)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        className="rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <button
        type="submit"
        className="rounded-lg bg-ember-500 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-ember-600"
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
    <div className="rounded-xl border border-ink-700 bg-ink-850 p-4">
      <p className="font-medium text-slate-100">{machine.name}</p>
      <p className="text-xs text-slate-500">
        {[machine.machine_type, machine.location].filter(Boolean).join(" · ") || "No details"}
      </p>

      <ul className="mt-3 space-y-1.5">
        {machine.implementations.map((impl) => (
          <li key={impl.id} className="flex items-center justify-between text-sm">
            <span className="text-slate-300">{impl.label}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[impl.status]}`}
            >
              {impl.status}
            </span>
          </li>
        ))}
        {machine.implementations.length === 0 && (
          <li className="text-sm text-slate-500">No implementations yet.</li>
        )}
      </ul>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          placeholder="New implementation label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="flex-1 rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
        />
        <button
          type="submit"
          className="rounded-lg bg-ink-700 px-3 py-1 text-sm font-medium text-slate-200 transition-colors hover:bg-ink-600"
        >
          Add
        </button>
      </form>
    </div>
  );
}
