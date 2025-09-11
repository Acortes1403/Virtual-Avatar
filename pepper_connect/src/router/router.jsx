import { createBrowserRouter } from "react-router-dom";
import HomePage from "../pages/HomePage";
import ConnectPage from "../pages/ConnectPage";
import VideoCall from "../pages/VideoCall";
import PepperView from "../pages/PepperView";

const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/connect", element: <ConnectPage /> },
  { path: "/videocall", element: <VideoCall /> },
  { path: "/pepper", element: <PepperView /> },

]);

export default router;
