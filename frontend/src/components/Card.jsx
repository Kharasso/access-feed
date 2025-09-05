import Badge from "./Badge";
import ScorePill from "./ScorePill";

export default function Card({ item }) {
  return (
    <a
      href={item.link}
      target="_blank"
      rel="noreferrer"
      className="block rounded-2xl border p-4 shadow-sm hover:shadow-md transition"
    >
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold leading-tight">
              {item.title}
            </h3>
            {item.event_type !== "Other" && <Badge>{item.event_type}</Badge>}
            {item.firms?.slice(0, 2).map((f) => (
              <Badge key={f}>{f}</Badge>
            ))}
            {item.relationship_badges?.slice(0, 1).map((b) => (
              <Badge key={b}>{b}</Badge>
            ))}
          </div>
          <p className="mt-2 text-sm text-gray-600 line-clamp-3">
            {item.summary}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {item.entities?.slice(0, 4).map((e) => (
              <Badge key={e}>{e}</Badge>
            ))}
          </div>
        </div>
        <ScorePill score={item.score} />
      </div>
    </a>
  );
}
