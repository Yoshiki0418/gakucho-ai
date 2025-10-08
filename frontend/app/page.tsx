export default function Page( ) {
    console.log("This line should trigger a lint error!") // ← セミコロンなし、console 使用、インデント崩れ

return (
<div>
    <h1>Lint Test Page</h1>
    <p>This page intentionally has lint errors.</p>
</div>
)
}