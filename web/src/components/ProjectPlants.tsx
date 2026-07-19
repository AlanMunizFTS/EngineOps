import { useState } from "react";

import type {
  ImplementationResponse,
  ImplementationStatus,
  MachineResponse,
  PlantResponse,
} from "../api/client";
import { BuildingIcon, FolderIcon } from "./icons";

export interface MachineWithImplementations extends MachineResponse {
  implementations: ImplementationResponse[];
}

export interface PlantWithMachines extends PlantResponse {
  machines: MachineWithImplementations[];
}

interface ProjectPlantsProps {
  plants: PlantWithMachines[];
  latestActivityLabel?: string;
  latestActivityAt?: string;
  onAddPlant: (name: string, location: string) => void;
  onAddMachine: (plantId: string, name: string, machineType: string, location: string) => void;
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

export default function ProjectPlants({
  plants,
  latestActivityLabel,
  latestActivityAt,
  onAddPlant,
  onAddMachine,
  onAddImplementation,
}: ProjectPlantsProps) {
  const [showForm, setShowForm] = useState(false);

  return (
    <section className="rounded-md border border-ink-800 bg-ink-900">
      {latestActivityLabel && (
        <div className="flex items-center gap-2 border-b border-ink-800 px-4 py-2.5 text-sm">
          <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-ember-500 text-[10px] font-semibold text-white">
            •
          </span>
          <span className="truncate text-slate-300">{latestActivityLabel}</span>
          {latestActivityAt && (
            <span className="ml-auto flex-shrink-0 text-xs text-slate-500">
              {latestActivityAt}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between border-b border-ink-800 px-4 py-2">
        <h2 className="text-sm font-semibold text-slate-200">Plants</h2>
        <button
          onClick={() => setShowForm((prev) => !prev)}
          className="text-xs font-medium text-ember-400 transition-colors hover:text-ember-300"
        >
          {showForm ? "Cancel" : "+ New plant"}
        </button>
      </div>

      {showForm && (
        <div className="border-b border-ink-800 px-4 py-3">
          <NewPlantForm
            onSubmit={(name, location) => {
              onAddPlant(name, location);
              setShowForm(false);
            }}
          />
        </div>
      )}

      <ul className="divide-y divide-ink-800">
        {plants.map((plant) => (
          <PlantRow
            key={plant.id}
            plant={plant}
            onAddMachine={onAddMachine}
            onAddImplementation={onAddImplementation}
          />
        ))}
        {plants.length === 0 && (
          <li className="px-4 py-6 text-sm text-slate-500">No plants attached yet.</li>
        )}
      </ul>
    </section>
  );
}

function NewPlantForm({ onSubmit }: { onSubmit: (name: string, location: string) => void }) {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit(name, location);
    setName("");
    setLocation("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
      <input
        type="text"
        placeholder="Plant name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        autoFocus
        className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <input
        type="text"
        placeholder="Location (optional)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <button
        type="submit"
        className="rounded-md bg-ember-500 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-ember-600"
      >
        Add
      </button>
    </form>
  );
}

function PlantRow({
  plant,
  onAddMachine,
  onAddImplementation,
}: {
  plant: PlantWithMachines;
  onAddMachine: (plantId: string, name: string, machineType: string, location: string) => void;
  onAddImplementation: (
    machineId: string,
    label: string,
    status: ImplementationStatus,
  ) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showMachineForm, setShowMachineForm] = useState(false);
  const machineCount = plant.machines.length;

  return (
    <li>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-ink-850"
      >
        <BuildingIcon className="h-4 w-4 flex-shrink-0 text-slate-500" />
        <span className="font-medium text-slate-200">{plant.name}</span>
        {plant.location && (
          <span className="truncate text-sm text-slate-500">{plant.location}</span>
        )}
        <span className="ml-auto flex-shrink-0 text-xs text-slate-500">
          {machineCount} machine{machineCount === 1 ? "" : "s"}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-ink-800 bg-ink-950/30 pl-7">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Machines
            </span>
            <button
              onClick={() => setShowMachineForm((prev) => !prev)}
              className="text-xs font-medium text-ember-400 transition-colors hover:text-ember-300"
            >
              {showMachineForm ? "Cancel" : "+ New machine"}
            </button>
          </div>

          {showMachineForm && (
            <div className="px-4 pb-3">
              <NewMachineForm
                onSubmit={(name, machineType, location) => {
                  onAddMachine(plant.id, name, machineType, location);
                  setShowMachineForm(false);
                }}
              />
            </div>
          )}

          <ul className="divide-y divide-ink-800 border-t border-ink-800">
            {plant.machines.map((machine) => (
              <MachineRow
                key={machine.id}
                machine={machine}
                onAddImplementation={onAddImplementation}
              />
            ))}
            {machineCount === 0 && (
              <li className="px-4 py-3 text-sm text-slate-500">No machines yet.</li>
            )}
          </ul>
        </div>
      )}
    </li>
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
        autoFocus
        className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <input
        type="text"
        placeholder="Type (optional)"
        value={machineType}
        onChange={(e) => setMachineType(e.target.value)}
        className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <input
        type="text"
        placeholder="Location (optional)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />
      <button
        type="submit"
        className="rounded-md bg-ember-500 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-ember-600"
      >
        Add
      </button>
    </form>
  );
}

function MachineRow({
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
  const [expanded, setExpanded] = useState(false);
  const [label, setLabel] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!label.trim()) return;
    onAddImplementation(machine.id, label, "planned");
    setLabel("");
  }

  const count = machine.implementations.length;

  return (
    <li>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-3 px-4 py-2 text-left transition-colors hover:bg-ink-850"
      >
        <FolderIcon className="h-4 w-4 flex-shrink-0 text-slate-500" />
        <span className="font-medium text-slate-200">{machine.name}</span>
        <span className="truncate text-sm text-slate-500">
          {[machine.machine_type, machine.location].filter(Boolean).join(" · ")}
        </span>
        <span className="ml-auto flex-shrink-0 text-xs text-slate-500">
          {count} implementation{count === 1 ? "" : "s"}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-ink-800 bg-ink-950/40 py-3 pl-11 pr-4">
          <ul className="space-y-1.5">
            {machine.implementations.map((impl) => (
              <li key={impl.id} className="flex items-center justify-between text-sm">
                <span className="text-slate-300">{impl.label}</span>
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLES[impl.status]}`}
                >
                  {impl.status}
                </span>
              </li>
            ))}
            {count === 0 && <li className="text-sm text-slate-500">No implementations yet.</li>}
          </ul>

          <form onSubmit={handleSubmit} className="mt-2 flex gap-2">
            <input
              type="text"
              placeholder="New implementation label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
            />
            <button
              type="submit"
              className="rounded-md bg-ink-700 px-3 py-1 text-sm font-medium text-slate-200 transition-colors hover:bg-ink-600"
            >
              Add
            </button>
          </form>
        </div>
      )}
    </li>
  );
}
