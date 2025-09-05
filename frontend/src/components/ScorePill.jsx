export default function ScorePill({ score }) {
return (
    <div className="ml-auto flex items-center rounded-full border px-2 py-0.5 text-xs">
        Relevance: <span className="ml-1 font-semibold">{score}%</span>
    </div>
    );
}