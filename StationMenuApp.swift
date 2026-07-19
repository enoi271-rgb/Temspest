// TEMSPEST STATION — Menu Bar controller (Swift, sem Xcode)
// Compilar: swiftc StationMenuApp.swift -o station_menu.app (ou correr swift StationMenuApp.swift)
// Mostra estado do servidor e permite ligar/desligar o LaunchAgent.

import AppKit
import Foundation

final class StationDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var timer: Timer?

    func applicationDidFinishLaunching(_ n: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        let menu = NSMenu()
        menu.addItem(withTitle: "TEMSPEST STATION", action: nil, keyEquivalent: "")
        menu.addItem(NSMenuItem.separator())
        let toggle = NSMenuItem(title: "Ligar / Desligar servidor", action: #selector(toggleServer), keyEquivalent: "t")
        toggle.target = self
        menu.addItem(toggle)
        let openMac = NSMenuItem(title: "Abrir no Mac (localhost)", action: #selector(openMac), keyEquivalent: "o")
        openMac.target = self
        menu.addItem(openMac)
        let openTunnel = NSMenuItem(title: "Abrir via Tunnel (URL público)", action: #selector(openTunnel), keyEquivalent: "u")
        openTunnel.target = self
        menu.addItem(openTunnel)
        menu.addItem(NSMenuItem.separator())
        let quit = NSMenuItem(title: "Sair deste menu (servidor fica)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quit)
        statusItem.menu = menu
        timer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in self?.refresh() }
        refresh()
    }

    func refresh() {
        let up = isUp()
        let title = up ? "💀 TEMSPEST: ON" : "💀 TEMSPEST: OFF"
        if let b = statusItem.button { b.title = title; b.appearsDisabled = !up }
    }

    func isUp() -> Bool {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
        p.arguments = ["-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:5050/station"]
        let pipe = Pipe(); p.standardOutput = pipe
        try? p.run(); p.waitUntilExit()
        let code = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? "000"
        return code.trimmingCharacters(in: .whitespaces) == "200"
    }

    @objc func toggleServer() {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/bash")
        task.arguments = ["-c", "if launchctl list | grep -q com.temspest.station; then launchctl unload -w ~/Library/LaunchAgents/com.temspest.station.plist; else launchctl load -w ~/Library/LaunchAgents/com.temspest.station.plist; fi"]
        try? task.run(); task.waitUntilExit()
        DispatchQueue.main.asyncAfter(deadline: .now()+2) { self.refresh() }
    }

    @objc func openMac() { NSWorkspace.shared.open(URL(string: "http://localhost:5050/station")!) }
    @objc func openTunnel() {
        // tenta ler o URL do tunnel do ficheiro tunnel_url.txt
        let urlFile = (NSHomeDirectory() as NSString).appendingPathComponent("TEMSPEST_STATION/tunnel_url.txt")
        if let u = try? String(contentsOfFile: urlFile, encoding: .utf8), !u.isEmpty {
            NSWorkspace.shared.open(URL(string: u.trimmingCharacters(in: .whitespacesAndNewlines))!)
        } else {
            NSWorkspace.shared.open(URL(string: "http://localhost:5050/station")!)
        }
    }
}

let app = NSApplication.shared
let del = StationDelegate()
app.delegate = del
app.run()
