import { GenreDetail } from "@/components/catalog/GenreDetail";

type Props = {
  params: Promise<{ genre: string }>;
};

export default async function GenrePage({ params }: Props) {
  const { genre } = await params;
  const slug = decodeURIComponent(genre);
  return <GenreDetail slug={slug} />;
}
