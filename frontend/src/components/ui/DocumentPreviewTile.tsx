import DocumentTile, { DocumentFile } from "@/components/documents/DocumentTile";

type Props = {
  file: DocumentFile;
  onClick?: () => void;
  className?: string;
};

export default function DocumentPreviewTile({ file, onClick, className }: Props) {
  return <DocumentTile file={file} onClick={onClick} className={className} />;
}
