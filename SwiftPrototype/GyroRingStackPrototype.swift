import Cocoa
import SceneKit
import QuartzCore

/// Minimal macOS SceneKit prototype that renders a nested gyro ring stack.
/// Run on macOS with:
///   swiftc GyroRingStackPrototype.swift -framework Cocoa -framework SceneKit -framework QuartzCore -o GyroRingStackPrototype
///   ./GyroRingStackPrototype

final class GyroPrototypeDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!

    func applicationDidFinishLaunching(_ notification: Notification) {
        let scene = SCNScene()

        // Camera
        let cameraNode = SCNNode()
        cameraNode.camera = SCNCamera()
        cameraNode.camera?.fieldOfView = 55
        cameraNode.position = SCNVector3(0, 0.6, 8)
        scene.rootNode.addChildNode(cameraNode)

        // Lighting
        let keyLight = SCNNode()
        keyLight.light = SCNLight()
        keyLight.light?.type = .omni
        keyLight.light?.intensity = 1300
        keyLight.position = SCNVector3(5, 6, 8)
        scene.rootNode.addChildNode(keyLight)

        let fillLight = SCNNode()
        fillLight.light = SCNLight()
        fillLight.light?.type = .omni
        fillLight.light?.intensity = 450
        fillLight.position = SCNVector3(-6, -2, 3)
        scene.rootNode.addChildNode(fillLight)

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light?.type = .ambient
        ambient.light?.color = NSColor(calibratedWhite: 0.15, alpha: 1.0)
        scene.rootNode.addChildNode(ambient)

        // Subtle center core for visual anchor.
        let core = SCNSphere(radius: 0.22)
        core.firstMaterial?.diffuse.contents = NSColor(calibratedRed: 0.86, green: 0.93, blue: 1.0, alpha: 1)
        core.firstMaterial?.metalness.contents = 0.15
        core.firstMaterial?.roughness.contents = 0.2
        let coreNode = SCNNode(geometry: core)
        scene.rootNode.addChildNode(coreNode)

        // Parent stack node lets us orbit the whole system.
        let stack = SCNNode()
        scene.rootNode.addChildNode(stack)

        addRing(
            to: stack,
            radius: 2.8,
            pipeRadius: 0.06,
            color: NSColor(calibratedRed: 1.0, green: 0.80, blue: 0.42, alpha: 1),
            euler: SCNVector3(0.35, 0.0, 0.15),
            spinDuration: 8.0,
            axis: SCNVector3(0, 1, 0)
        )

        addRing(
            to: stack,
            radius: 2.1,
            pipeRadius: 0.055,
            color: NSColor(calibratedRed: 0.37, green: 0.86, blue: 0.96, alpha: 1),
            euler: SCNVector3(-0.25, 0.1, -0.2),
            spinDuration: 6.0,
            axis: SCNVector3(1, 0, 0)
        )

        addRing(
            to: stack,
            radius: 1.45,
            pipeRadius: 0.05,
            color: NSColor(calibratedRed: 0.98, green: 0.55, blue: 0.30, alpha: 1),
            euler: SCNVector3(0.15, -0.35, 0.4),
            spinDuration: 4.8,
            axis: SCNVector3(0, 0, 1)
        )

        addRing(
            to: stack,
            radius: 0.85,
            pipeRadius: 0.045,
            color: NSColor(calibratedRed: 0.78, green: 0.84, blue: 1.0, alpha: 1),
            euler: SCNVector3(-0.5, 0.2, 0.0),
            spinDuration: 3.6,
            axis: SCNVector3(1, 1, 0)
        )

        // Gentle global precession.
        let precess = CABasicAnimation(keyPath: "rotation")
        precess.toValue = NSValue(scnVector4: SCNVector4(0, 1, 0, .pi * 2))
        precess.duration = 24
        precess.repeatCount = .infinity
        precess.timingFunction = CAMediaTimingFunction(name: .linear)
        stack.addAnimation(precess, forKey: "stack.precession")

        let view = SCNView(frame: NSRect(x: 0, y: 0, width: 1080, height: 720))
        view.scene = scene
        view.backgroundColor = NSColor(calibratedRed: 0.02, green: 0.03, blue: 0.08, alpha: 1)
        view.antialiasingMode = .multisampling4X
        view.rendersContinuously = true
        view.allowsCameraControl = true
        view.defaultCameraController.interactionMode = .orbitTurntable

        window = NSWindow(
            contentRect: view.frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "SceneKit Gyro Ring Stack Prototype"
        window.center()
        window.contentView = view
        window.makeKeyAndOrderFront(nil)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    private func addRing(
        to parent: SCNNode,
        radius: CGFloat,
        pipeRadius: CGFloat,
        color: NSColor,
        euler: SCNVector3,
        spinDuration: CFTimeInterval,
        axis: SCNVector3
    ) {
        let torus = SCNTorus(ringRadius: radius, pipeRadius: pipeRadius)
        let material = SCNMaterial()
        material.diffuse.contents = color
        material.metalness.contents = 0.75
        material.roughness.contents = 0.25
        material.emission.contents = color.withAlphaComponent(0.15)
        torus.materials = [material]

        let node = SCNNode(geometry: torus)
        node.eulerAngles = euler
        parent.addChildNode(node)

        let spin = CABasicAnimation(keyPath: "rotation")
        spin.toValue = NSValue(scnVector4: SCNVector4(axis.x, axis.y, axis.z, .pi * 2))
        spin.duration = spinDuration
        spin.repeatCount = .infinity
        spin.timingFunction = CAMediaTimingFunction(name: .linear)
        node.addAnimation(spin, forKey: "ring.spin")
    }
}

let app = NSApplication.shared
let delegate = GyroPrototypeDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()
