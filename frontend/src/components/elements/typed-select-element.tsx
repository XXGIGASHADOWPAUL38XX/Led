"use client";

import { SelectElement } from "./select-element";

export type TypedSelectElementProps<T> = {
  label: string;
  value: T;
  onValueChange: (value: T) => void;
  options: readonly { value: T; label: string }[];
  disabled?: boolean;
};

export function TypedSelectElement<T>({ value, onValueChange, options, ...props }: TypedSelectElementProps<T>) {
  const index = options.findIndex((option) => JSON.stringify(option.value) === JSON.stringify(value));
  return <SelectElement {...props} value={index < 0 ? "" : String(index)}
    options={options.map((option, at) => ({ value: String(at), label: option.label }))}
    onValueChange={(selected) => onValueChange(options[Number(selected)].value)} />;
}

export function AxisElement(props: Omit<TypedSelectElementProps<number | number[] | null>, "options"> & { axes?: readonly number[] }) {
  const { axes = [0, 1], ...rest } = props;
  const options: { value: number | number[] | null; label: string }[] = [
    { value: null, label: "All axes" }, ...axes.map((axis) => ({ value: axis, label: `Axis ${axis}` })),
  ];
  if (Array.isArray(props.value)) options.push({ value: props.value, label: `Axes ${props.value.join(", ")}` });
  return <TypedSelectElement {...rest} options={options} />;
}

export function OperatorElement(props: Omit<TypedSelectElementProps<string>, "options">) {
  return <TypedSelectElement {...props} options={["+", "-", "*", "/", "**", "<", "<=", "==", ">=", ">", "&", "|", "(", ")"].map((value) => ({ value, label: value }))} />;
}

export const EnumElement = TypedSelectElement;
