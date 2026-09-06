import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import UploadPage from "./pages/Upload_page.jsx";
import MeetingsListPage from "./pages/Meetingslist_page.jsx";
import TranscriptPage from "./pages/Transcript_page.jsx";
import ChatPage from "./pages/Chat_page.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/meetings" element={<MeetingsListPage />} />
          <Route path="/meetings/:id" element={<TranscriptPage />} />
          <Route path="/meetings/:id/chat" element={<ChatPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}