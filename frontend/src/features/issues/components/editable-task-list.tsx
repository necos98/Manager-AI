import { useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Trash2, Plus, Loader2, Check, Circle, Clock } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  useUpdateTask,
  useDeleteTask,
  useCreateTasks,
  useReplaceTasks,
} from "@/features/issues/hooks";
import type { Task, TaskCreate } from "@/shared/types";

interface SortableTaskItemProps {
  task: Task;
  onToggle: (task: Task) => void;
  onDelete: (taskId: string) => void;
  isToggling: boolean;
  isDeleting: boolean;
}

function SortableTaskItem({
  task,
  onToggle,
  onDelete,
  isToggling,
  isDeleting,
}: SortableTaskItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const statusIcon =
    task.status === "Completed" ? (
      <Check className="size-4 text-emerald-500" />
    ) : task.status === "In Progress" ? (
      <Clock className="size-4 text-amber-500" />
    ) : (
      <Circle className="size-4 text-slate-400" />
    );

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 p-2 rounded-md border bg-card hover:bg-accent/50 group"
    >
      <button
        className="cursor-grab touch-none text-muted-foreground"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-4" />
      </button>

      <button
        onClick={() => onToggle(task)}
        disabled={isToggling || task.status === "Completed"}
        className="shrink-0 disabled:opacity-50"
        title={task.status === "Completed" ? "Completato" : "Segna come completato"}
      >
        {isToggling ? <Loader2 className="size-4 animate-spin" /> : statusIcon}
      </button>

      <span
        className={`flex-1 text-sm ${
          task.status === "Completed" ? "line-through text-muted-foreground" : ""
        }`}
      >
        {task.name}
      </span>

      <button
        onClick={() => onDelete(task.id)}
        disabled={isDeleting}
        className="opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive/80 disabled:opacity-50"
      >
        {isDeleting ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
      </button>
    </div>
  );
}

interface EditableTaskListProps {
  tasks: Task[];
  projectId: string;
  issueId: string;
}

export function EditableTaskList({ tasks, projectId, issueId }: EditableTaskListProps) {
  const [newTaskName, setNewTaskName] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const updateTask = useUpdateTask(projectId, issueId);
  const deleteTask = useDeleteTask(projectId, issueId);
  const createTasks = useCreateTasks(projectId, issueId);
  const replaceTasks = useReplaceTasks(projectId, issueId);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleToggle = async (task: Task) => {
    setTogglingId(task.id);
    try {
      if (task.status === "Pending") {
        await updateTask.mutateAsync({ taskId: task.id, data: { status: "In Progress" } });
        await updateTask.mutateAsync({ taskId: task.id, data: { status: "Completed" } });
      } else if (task.status === "In Progress") {
        await updateTask.mutateAsync({ taskId: task.id, data: { status: "Completed" } });
      }
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (taskId: string) => {
    setDeletingId(taskId);
    try {
      await deleteTask.mutateAsync(taskId);
    } finally {
      setDeletingId(null);
    }
  };

  const handleAddTask = () => {
    if (!newTaskName.trim()) return;
    createTasks.mutate([{ name: newTaskName.trim() }], {
      onSuccess: () => setNewTaskName(""),
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = tasks.findIndex((t) => t.id === active.id);
    const newIndex = tasks.findIndex((t) => t.id === over.id);
    const reordered = arrayMove(tasks, oldIndex, newIndex);
    replaceTasks.mutate(reordered.map((t): TaskCreate => ({ name: t.name })));
  };

  return (
    <div className="space-y-2">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <SortableTaskItem
              key={task.id}
              task={task}
              onToggle={handleToggle}
              onDelete={handleDelete}
              isToggling={togglingId === task.id}
              isDeleting={deletingId === task.id}
            />
          ))}
        </SortableContext>
      </DndContext>

      {tasks.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-4">
          Nessun task. Aggiungine uno qui sotto.
        </p>
      )}

      <div className="flex gap-2 mt-3">
        <Input
          placeholder="Aggiungi task..."
          value={newTaskName}
          onChange={(e) => setNewTaskName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAddTask();
          }}
          className="flex-1"
        />
        <Button
          size="sm"
          onClick={handleAddTask}
          disabled={!newTaskName.trim() || createTasks.isPending}
        >
          {createTasks.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Plus className="size-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
