import SpriteKit

class GameScene: SKScene, SKPhysicsContactDelegate {

    // MARK: - Category Bitmasks

    private struct Category {
        static let ball:   UInt32 = 0x1 << 0
        static let paddle: UInt32 = 0x1 << 1
        static let block:  UInt32 = 0x1 << 2
        static let wall:   UInt32 = 0x1 << 3
        static let bottom: UInt32 = 0x1 << 4
    }

    // MARK: - Properties

    private var paddle: SKSpriteNode!
    private var ball: SKSpriteNode!
    private var scoreLabel: SKLabelNode!
    private var livesLabel: SKLabelNode!
    private var messageLabel: SKLabelNode!

    private var score = 0
    private var lives = 3
    private var blockCount = 0
    private var isPlaying = false

    private let ballSpeed: CGFloat = 500
    private let rows = 5
    private let cols = 8

    // MARK: - Scene Lifecycle

    override func didMove(to view: SKView) {
        backgroundColor = SKColor(red: 0.05, green: 0.05, blue: 0.15, alpha: 1.0)

        physicsWorld.gravity = .zero
        physicsWorld.contactDelegate = self
        physicsBody = SKPhysicsBody(edgeLoopFrom: frame)
        physicsBody?.categoryBitMask = Category.wall
        physicsBody?.friction = 0

        setupBottomEdge()
        setupPaddle()
        setupBall()
        setupBlocks()
        setupLabels()
        showMessage("タップしてスタート")
    }

    // MARK: - Setup

    private func setupBottomEdge() {
        let bottomRect = CGRect(x: frame.minX, y: frame.minY - 10, width: frame.width, height: 1)
        let bottom = SKNode()
        bottom.physicsBody = SKPhysicsBody(edgeLoopFrom: bottomRect)
        bottom.physicsBody?.categoryBitMask = Category.bottom
        bottom.physicsBody?.contactTestBitMask = Category.ball
        addChild(bottom)
    }

    private func setupPaddle() {
        let paddleWidth = frame.width * 0.22
        let paddleHeight: CGFloat = 16

        paddle = SKSpriteNode(color: .white, size: CGSize(width: paddleWidth, height: paddleHeight))
        paddle.position = CGPoint(x: frame.midX, y: frame.minY + 60)
        paddle.physicsBody = SKPhysicsBody(rectangleOf: paddle.size)
        paddle.physicsBody?.isDynamic = false
        paddle.physicsBody?.categoryBitMask = Category.paddle
        paddle.physicsBody?.contactTestBitMask = Category.ball
        paddle.physicsBody?.friction = 0
        paddle.physicsBody?.restitution = 1.0
        addChild(paddle)
    }

    private func setupBall() {
        let radius: CGFloat = 10
        ball = SKSpriteNode(color: .systemYellow, size: CGSize(width: radius * 2, height: radius * 2))
        ball.position = CGPoint(x: frame.midX, y: paddle.position.y + 30)

        ball.physicsBody = SKPhysicsBody(circleOfRadius: radius)
        ball.physicsBody?.isDynamic = true
        ball.physicsBody?.affectedByGravity = false
        ball.physicsBody?.allowsRotation = false
        ball.physicsBody?.friction = 0
        ball.physicsBody?.restitution = 1.0
        ball.physicsBody?.linearDamping = 0
        ball.physicsBody?.angularDamping = 0
        ball.physicsBody?.categoryBitMask = Category.ball
        ball.physicsBody?.contactTestBitMask = Category.block | Category.paddle | Category.bottom
        ball.physicsBody?.collisionBitMask = Category.wall | Category.paddle | Category.block
        addChild(ball)
    }

    private func setupBlocks() {
        let margin: CGFloat = 4
        let topOffset = frame.maxY - 140
        let totalWidth = frame.width - margin * 2
        let blockWidth = (totalWidth - margin * CGFloat(cols - 1)) / CGFloat(cols)
        let blockHeight: CGFloat = 20

        let colors: [SKColor] = [
            .systemRed, .systemOrange, .systemYellow, .systemGreen, .systemCyan
        ]

        blockCount = 0

        for row in 0..<rows {
            for col in 0..<cols {
                let x = margin + blockWidth / 2 + CGFloat(col) * (blockWidth + margin)
                let y = topOffset - CGFloat(row) * (blockHeight + margin)

                let block = SKSpriteNode(
                    color: colors[row % colors.count],
                    size: CGSize(width: blockWidth, height: blockHeight)
                )
                block.position = CGPoint(x: x, y: y)
                block.name = "block"
                block.physicsBody = SKPhysicsBody(rectangleOf: block.size)
                block.physicsBody?.isDynamic = false
                block.physicsBody?.categoryBitMask = Category.block
                block.physicsBody?.contactTestBitMask = Category.ball
                block.physicsBody?.friction = 0
                block.physicsBody?.restitution = 1.0
                addChild(block)
                blockCount += 1
            }
        }
    }

    private func setupLabels() {
        scoreLabel = SKLabelNode(fontNamed: "Helvetica Neue Bold")
        scoreLabel.fontSize = 20
        scoreLabel.fontColor = .white
        scoreLabel.horizontalAlignmentMode = .left
        scoreLabel.position = CGPoint(x: frame.minX + 16, y: frame.maxY - 50)
        updateScoreLabel()
        addChild(scoreLabel)

        livesLabel = SKLabelNode(fontNamed: "Helvetica Neue Bold")
        livesLabel.fontSize = 20
        livesLabel.fontColor = .white
        livesLabel.horizontalAlignmentMode = .right
        livesLabel.position = CGPoint(x: frame.maxX - 16, y: frame.maxY - 50)
        updateLivesLabel()
        addChild(livesLabel)

        messageLabel = SKLabelNode(fontNamed: "Helvetica Neue Bold")
        messageLabel.fontSize = 28
        messageLabel.fontColor = .systemYellow
        messageLabel.position = CGPoint(x: frame.midX, y: frame.midY)
        messageLabel.isHidden = true
        addChild(messageLabel)
    }

    // MARK: - Label Updates

    private func updateScoreLabel() {
        scoreLabel.text = "スコア: \(score)"
    }

    private func updateLivesLabel() {
        livesLabel.text = "ライフ: \(lives)"
    }

    private func showMessage(_ text: String) {
        messageLabel.text = text
        messageLabel.isHidden = false
    }

    private func hideMessage() {
        messageLabel.isHidden = true
    }

    // MARK: - Game Flow

    private func launchBall() {
        isPlaying = true
        hideMessage()
        let angle = CGFloat.random(in: CGFloat.pi / 4 ... CGFloat.pi * 3 / 4)
        let dx = ballSpeed * cos(angle)
        let dy = ballSpeed * sin(angle)
        ball.physicsBody?.velocity = CGVector(dx: dx, dy: dy)
    }

    private func resetBall() {
        ball.physicsBody?.velocity = .zero
        ball.position = CGPoint(x: frame.midX, y: paddle.position.y + 30)
        isPlaying = false
    }

    private func loseLife() {
        lives -= 1
        updateLivesLabel()

        if lives <= 0 {
            gameOver()
        } else {
            resetBall()
            showMessage("タップして再開")
        }
    }

    private func gameOver() {
        resetBall()
        showMessage("ゲームオーバー\nタップでリトライ")
        isPlaying = false
    }

    private func gameClear() {
        resetBall()
        showMessage("クリア! スコア: \(score)\nタップでリトライ")
        isPlaying = false
    }

    private func resetGame() {
        score = 0
        lives = 3
        updateScoreLabel()
        updateLivesLabel()

        enumerateChildNodes(withName: "block") { node, _ in
            node.removeFromParent()
        }
        setupBlocks()
        resetBall()
    }

    // MARK: - Touch Handling

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        if !isPlaying {
            if lives <= 0 || blockCount <= 0 {
                resetGame()
            }
            launchBall()
            return
        }

        if let touch = touches.first {
            movePaddle(to: touch.location(in: self))
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        if let touch = touches.first {
            movePaddle(to: touch.location(in: self))
        }
    }

    private func movePaddle(to location: CGPoint) {
        let halfWidth = paddle.size.width / 2
        let clampedX = max(frame.minX + halfWidth, min(location.x, frame.maxX - halfWidth))
        paddle.position.x = clampedX
    }

    // MARK: - Physics Contact

    func didBegin(_ contact: SKPhysicsContact) {
        let bodyA = contact.bodyA
        let bodyB = contact.bodyB

        let mask = bodyA.categoryBitMask | bodyB.categoryBitMask

        if mask == (Category.ball | Category.block) {
            let blockBody = bodyA.categoryBitMask == Category.block ? bodyA : bodyB
            if let blockNode = blockBody.node {
                destroyBlock(blockNode)
            }
        }

        if mask == (Category.ball | Category.bottom) {
            loseLife()
        }

        if mask == (Category.ball | Category.paddle) {
            adjustBallAngle()
        }
    }

    private func destroyBlock(_ node: SKNode) {
        let particles = SKEmitterNode()
        particles.particleBirthRate = 40
        particles.numParticlesToEmit = 8
        particles.particleLifetime = 0.4
        particles.particleSpeed = 80
        particles.particleSpeedRange = 40
        particles.emissionAngleRange = CGFloat.pi * 2
        particles.particleSize = CGSize(width: 4, height: 4)
        particles.particleColor = (node as? SKSpriteNode)?.color ?? .white
        particles.particleColorBlendFactor = 1.0
        particles.particleAlphaSpeed = -2.0
        particles.position = node.position
        addChild(particles)
        particles.run(.sequence([.wait(forDuration: 0.5), .removeFromParent()]))

        node.removeFromParent()
        blockCount -= 1
        score += 10
        updateScoreLabel()

        if blockCount <= 0 {
            gameClear()
        }
    }

    private func adjustBallAngle() {
        guard let velocity = ball.physicsBody?.velocity else { return }
        let offsetX = ball.position.x - paddle.position.x
        let normalizedOffset = offsetX / (paddle.size.width / 2)
        let maxAngle: CGFloat = CGFloat.pi / 3
        let angle = normalizedOffset * maxAngle

        let speed = sqrt(velocity.dx * velocity.dx + velocity.dy * velocity.dy)
        let clampedSpeed = max(ballSpeed, speed)
        let dx = sin(angle) * clampedSpeed
        let dy = abs(cos(angle) * clampedSpeed)

        ball.physicsBody?.velocity = CGVector(dx: dx, dy: dy)
    }

    // MARK: - Update

    override func update(_ currentTime: TimeInterval) {
        guard isPlaying, let velocity = ball.physicsBody?.velocity else { return }

        let speed = sqrt(velocity.dx * velocity.dx + velocity.dy * velocity.dy)

        // Keep ball speed consistent
        if speed < ballSpeed * 0.9 || speed > ballSpeed * 1.1 {
            let factor = ballSpeed / max(speed, 0.001)
            ball.physicsBody?.velocity = CGVector(
                dx: velocity.dx * factor,
                dy: velocity.dy * factor
            )
        }

        // Prevent nearly horizontal movement
        let minVerticalSpeed: CGFloat = ballSpeed * 0.3
        if abs(velocity.dy) < minVerticalSpeed {
            let sign: CGFloat = velocity.dy >= 0 ? 1 : -1
            let newDy = sign * minVerticalSpeed
            let newDx = sqrt(ballSpeed * ballSpeed - newDy * newDy) * (velocity.dx >= 0 ? 1 : -1)
            ball.physicsBody?.velocity = CGVector(dx: newDx, dy: newDy)
        }
    }
}
