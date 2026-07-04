type Props = {
  message: string;
};

export function EmptyState({ message }: Props) {
  return <p className="empty">{message}</p>;
}
